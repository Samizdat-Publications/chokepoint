<original_task>
HOR-5: Build MVP frontend: Strait of Hormuz map + price chart.

Build the initial Next.js 15 frontend that visualizes the two core ChokePoint datasets:
1. Mapbox GL map centered on Strait of Hormuz showing vessel positions as dots
2. Time-series chart (Recharts): Brent crude price vs. daily tanker transit count
3. Basic responsive layout with Tailwind CSS
4. API routes to serve data from TimescaleDB
5. Deploy to Vercel

Phase 1 milestone: live map with vessel dots + price chart updating daily. Designed for non-expert audience — clean and legible.
</original_task>

<work_completed>
## This is the first heartbeat on HOR-5 — no frontend code exists yet.

### Prior work in repo (complete, committed at 4585a2a):
- `db/schema/002_vessel_positions.sql`: `vessel_positions` hypertable + `daily_hormuz_transits` continuous aggregate view
- `db/schema/003_oil_prices.sql`: `oil_prices` hypertable
- `pipelines/vessel_positions/`: Full AIS ingestion pipeline (aisstream.io + MarineTraffic adapters)
- `pipelines/common/config.py`: Config singleton with DATABASE_URL, AIS keys, bounding box settings
- `pipelines/common/db.py`: asyncpg pool management

### Workspace current state:
- Workspace root: `C:\Users\stewa\.paperclip\instances\default\workspaces\bcc3904f-fffb-4043-aa1a-40ebbc8c7853`
- Only directories at root: `db/`, `pipelines/`, `whats-next.md`, `README.md`
- No `frontend/` directory exists
- Git is clean (no uncommitted changes)
- Branch: master

### Issue metadata:
- Issue ID: `72efcbb5-6e3f-431c-91f5-6c8eac769104`
- Run ID: `7353e950-d77f-45c8-9d5b-beca0bd5580e` (changes each heartbeat — check wake payload)
- Paperclip base URL: `http://127.0.0.1:3100`
- Auth: `Authorization: Bearer $PAPERCLIP_API_KEY`
- Agent ID: `bcc3904f-fffb-4043-aa1a-40ebbc8c7853` (CTO)
- Company ID: `30303548-3beb-45ac-a484-e568fe73683e`
</work_completed>

<work_remaining>
## All HOR-5 work is remaining. Ordered by dependency:

---

### Step 1: Scaffold Next.js 15 app

```bash
cd C:\Users\stewa\.paperclip\instances\default\workspaces\bcc3904f-fffb-4043-aa1a-40ebbc8c7853
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

Resulting structure:
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── api/
│       ├── vessels/latest/route.ts
│       └── chart/daily/route.ts
├── components/
│   ├── HormuzMap.tsx
│   └── PriceTransitChart.tsx
├── lib/
│   └── db.ts
├── .env.local
├── next.config.ts
└── package.json
```

---

### Step 2: Install dependencies

```bash
cd frontend
npm install mapbox-gl @types/mapbox-gl
npm install recharts
npm install pg @types/pg
```

- `mapbox-gl`: Mapbox GL JS for the map
- `recharts`: React charting library for the price/transit chart
- `pg`: Node.js PostgreSQL client (server-side DB access in API routes)

---

### Step 3: Create `frontend/lib/db.ts`

Server-side DB pool using `pg` (NOT asyncpg — that's Python only):

```typescript
// frontend/lib/db.ts
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export default pool;
```

---

### Step 4: Create `frontend/app/api/vessels/latest/route.ts`

Returns latest vessel position for each active MMSI (for map dots). Query returns vessels seen in the last 2 hours:

```typescript
import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  const result = await pool.query(`
    SELECT DISTINCT ON (mmsi)
      mmsi,
      vessel_name,
      vessel_type,
      lat,
      lon,
      speed,
      heading,
      time
    FROM vessel_positions
    WHERE time > NOW() - INTERVAL '2 hours'
      AND vessel_type IN ('VLCC', 'Suezmax', 'Tanker')
    ORDER BY mmsi, time DESC
  `);
  return NextResponse.json(result.rows);
}
```

---

### Step 5: Create `frontend/app/api/chart/daily/route.ts`

Returns last 90 days of Brent price + daily transit count, joined on date:

```typescript
import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  const result = await pool.query(`
    SELECT
      p.day,
      p.brent_price,
      COALESCE(t.vessel_count, 0) AS vessel_count
    FROM (
      SELECT
        time_bucket('1 day', time) AS day,
        AVG(price) AS brent_price
      FROM oil_prices
      WHERE series_id = 'BRENT_SPOT'
        AND time > NOW() - INTERVAL '90 days'
      GROUP BY day
    ) p
    LEFT JOIN (
      SELECT day, SUM(vessel_count) AS vessel_count
      FROM daily_hormuz_transits
      WHERE day > NOW() - INTERVAL '90 days'
      GROUP BY day
    ) t ON p.day = t.day
    ORDER BY p.day ASC
  `);
  return NextResponse.json(result.rows);
}
```

---

### Step 6: Create `frontend/components/HormuzMap.tsx`

Mapbox GL map component. Center: [56.3, 26.65] (middle of Strait), zoom 8.

```typescript
'use client';
import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;

type Vessel = {
  mmsi: number;
  vessel_name: string | null;
  vessel_type: string | null;
  lat: number;
  lon: number;
  speed: number | null;
};

export default function HormuzMap({ vessels }: { vessels: Vessel[] }) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (map.current || !mapContainer.current) return;
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [56.3, 26.65],
      zoom: 8,
    });

    map.current.on('load', () => {
      // Add vessels as GeoJSON circles
      const geojson: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: vessels.map(v => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [v.lon, v.lat] },
          properties: {
            mmsi: v.mmsi,
            name: v.vessel_name || `MMSI ${v.mmsi}`,
            type: v.vessel_type || 'Unknown',
            speed: v.speed ?? 0,
          },
        })),
      };

      map.current!.addSource('vessels', { type: 'geojson', data: geojson });
      map.current!.addLayer({
        id: 'vessel-dots',
        type: 'circle',
        source: 'vessels',
        paint: {
          'circle-radius': 6,
          'circle-color': [
            'match', ['get', 'type'],
            'VLCC', '#f97316',
            'Suezmax', '#3b82f6',
            '#22c55e',
          ],
          'circle-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
        },
      });
    });
  }, [vessels]);

  return <div ref={mapContainer} className="w-full h-full" />;
}
```

---

### Step 7: Create `frontend/components/PriceTransitChart.tsx`

Dual-axis Recharts line chart. Left Y: Brent price (USD/bbl), Right Y: tanker count.

```typescript
'use client';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

type DataPoint = {
  day: string;
  brent_price: number;
  vessel_count: number;
};

export default function PriceTransitChart({ data }: { data: DataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data}>
        <XAxis
          dataKey="day"
          tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
        />
        <YAxis
          yAxisId="price"
          orientation="left"
          tickFormatter={(v) => `$${v}`}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          domain={['auto', 'auto']}
        />
        <YAxis
          yAxisId="vessels"
          orientation="right"
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          domain={[0, 'auto']}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }}
          labelFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <Legend wrapperStyle={{ color: '#9ca3af' }} />
        <Line
          yAxisId="price"
          type="monotone"
          dataKey="brent_price"
          name="Brent Crude (USD/bbl)"
          stroke="#f97316"
          dot={false}
          strokeWidth={2}
        />
        <Line
          yAxisId="vessels"
          type="monotone"
          dataKey="vessel_count"
          name="Daily Tanker Transits"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

---

### Step 8: Build `frontend/app/page.tsx`

Server component that fetches both datasets and renders map + chart:

```typescript
import HormuzMap from '@/components/HormuzMap';
import PriceTransitChart from '@/components/PriceTransitChart';

async function getVessels() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL}/api/vessels/latest`, {
    next: { revalidate: 300 }, // Revalidate every 5 minutes
  });
  if (!res.ok) return [];
  return res.json();
}

async function getChartData() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL}/api/chart/daily`, {
    next: { revalidate: 3600 }, // Revalidate every hour
  });
  if (!res.ok) return [];
  return res.json();
}

export default async function Home() {
  const [vessels, chartData] = await Promise.all([getVessels(), getChartData()]);

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <header className="px-6 py-4 border-b border-gray-800">
        <h1 className="text-2xl font-bold tracking-tight">ChokePoint</h1>
        <p className="text-gray-400 text-sm mt-1">
          Strait of Hormuz tanker traffic vs. Brent crude prices
        </p>
      </header>

      <div className="p-6 space-y-8">
        {/* Map section */}
        <section>
          <h2 className="text-lg font-semibold mb-3">
            Live Vessel Positions
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({vessels.length} tankers tracked)
            </span>
          </h2>
          <div className="w-full h-[480px] rounded-xl overflow-hidden border border-gray-800">
            <HormuzMap vessels={vessels} />
          </div>
          <div className="mt-2 flex gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-orange-500"></span>VLCC</span>
            <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-blue-500"></span>Suezmax</span>
            <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>Other Tanker</span>
          </div>
        </section>

        {/* Chart section */}
        <section>
          <h2 className="text-lg font-semibold mb-3">
            Brent Crude vs. Daily Transit Count
            <span className="ml-2 text-sm font-normal text-gray-400">Last 90 days</span>
          </h2>
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
            <PriceTransitChart data={chartData} />
          </div>
        </section>
      </div>
    </main>
  );
}
```

**IMPORTANT**: The `fetch()` calls above use `NEXT_PUBLIC_BASE_URL`. For Vercel this is set automatically via `VERCEL_URL`. Add this to `next.config.ts`:
```typescript
const nextConfig = {
  env: {
    NEXT_PUBLIC_BASE_URL: process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : 'http://localhost:3000',
  },
};
```

---

### Step 9: Create `frontend/.env.local`

```
DATABASE_URL=postgresql://...
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...
```

These are not committed. Add to `.gitignore`:
```
.env.local
.env*.local
```

---

### Step 10: Update `frontend/next.config.ts`

```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_BASE_URL: process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : 'http://localhost:3000',
  },
  // Mapbox GL uses browser globals — must be client-side only
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      'mapbox-gl': 'mapbox-gl',
    };
    return config;
  },
};

export default nextConfig;
```

---

### Step 11: Verify `frontend/app/layout.tsx`

The scaffolded layout should already have Tailwind globals. Ensure dark background default by wrapping in `bg-gray-950` or setting it in `globals.css`.

---

### Step 12: Local dev test

```bash
cd frontend
npm run dev
# Open http://localhost:3000
# Map should render (may be empty if no vessels in DB)
# Chart should render (may be empty if no prices in DB)
```

---

### Step 13: Deploy to Vercel

```bash
cd frontend
npx vercel
```

Set environment variables in Vercel dashboard:
- `DATABASE_URL` — TimescaleDB connection string (must be reachable from Vercel; use Neon, Supabase, or connection pooler)
- `NEXT_PUBLIC_MAPBOX_TOKEN` — Mapbox public token

---

### Step 14: Post-work (Paperclip)

After Vercel deployment URL is confirmed:

```bash
# Get issue ID (already known: 72efcbb5-6e3f-431c-91f5-6c8eac769104)

# Comment on HOR-5
curl -X POST "http://127.0.0.1:3100/api/companies/30303548-3beb-45ac-a484-e568fe73683e/issues/72efcbb5-6e3f-431c-91f5-6c8eac769104/comments" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"body":"Implemented MVP frontend under frontend/. Next.js 15 App Router with TypeScript + Tailwind. Two API routes: /api/vessels/latest (last-2hr vessel dots for Mapbox GL map) and /api/chart/daily (90-day Brent price + tanker transit count dual-axis Recharts chart). Dark theme, responsive layout. Deployed to Vercel. Mapbox token required in NEXT_PUBLIC_MAPBOX_TOKEN env var."}'

# Mark done
curl -X PATCH "http://127.0.0.1:3100/api/companies/30303548-3beb-45ac-a484-e568fe73683e/issues/72efcbb5-6e3f-431c-91f5-6c8eac769104" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status":"done"}'
```
</work_remaining>

<attempted_approaches>
- No implementation attempts made — this is the first heartbeat on HOR-5.
- No dead ends to report.
- HOR-2 (repo scaffolding) is marked `in_progress` in Paperclip but no Next.js code was ever committed — the workspace only contains `db/`, `pipelines/`, and `whats-next.md`. This is expected; the agent that ran HOR-2 likely planned without implementing. HOR-5 must create the entire frontend from scratch.
</attempted_approaches>

<critical_context>
## Paperclip API
- Base URL: `http://127.0.0.1:3100`
- Auth: `Authorization: Bearer $PAPERCLIP_API_KEY`
- Correct issue path: `/api/companies/{companyId}/issues/{issueId}/...`
- Wrong path (returns error): `/api/issues/...`
- HOR-5 Issue ID: `72efcbb5-6e3f-431c-91f5-6c8eac769104`
- Run ID: `7353e950-d77f-45c8-9d5b-beca0bd5580e` (may change each heartbeat — check wake payload)
- Agent ID: `bcc3904f-fffb-4043-aa1a-40ebbc8c7853` (CTO)
- Company ID: `30303548-3beb-45ac-a484-e568fe73683e`
- Issue already checked out — do NOT call checkout again

## Project Context
- **ChokePoint**: public intelligence platform correlating Strait of Hormuz tanker traffic with global oil prices
- Audience: non-experts — keep visualization clean and legible
- Phase 1 milestone: live map with vessel dots + price chart updating daily

## DB Schema (read-only reference, already migrated)

### vessel_positions (hypertable)
| Column | Type | Notes |
|--------|------|-------|
| time | TIMESTAMPTZ | Partition key |
| mmsi | BIGINT | Vessel identifier |
| vessel_name | TEXT | May be NULL |
| vessel_type | TEXT | 'VLCC', 'Suezmax', 'Tanker' |
| lat | DOUBLE PRECISION | WGS84 degrees |
| lon | DOUBLE PRECISION | WGS84 degrees |
| speed | REAL | Knots |
| heading | REAL | Degrees true |
| source | TEXT | 'aisstream' default |

### daily_hormuz_transits (continuous aggregate view — use this for chart, NOT raw vessel_positions)
| Column | Type | Notes |
|--------|------|-------|
| day | TIMESTAMPTZ | 1-day bucket |
| vessel_type | TEXT | |
| vessel_count | BIGINT | Distinct MMSIs |
| position_count | BIGINT | |
| avg_speed_knots | DOUBLE PRECISION | |

### oil_prices (hypertable)
| Column | Type | Notes |
|--------|------|-------|
| time | TIMESTAMPTZ | |
| series_id | TEXT | 'BRENT_SPOT', 'WTI_SPOT', 'RETAIL_GASOLINE_US' |
| source | TEXT | 'eia', 'fred', 'alpha_vantage' |
| price | DOUBLE PRECISION | |
| currency | TEXT | 'USD' default |
| unit | TEXT | 'barrel', 'gallon', 'mmbtu' |

## Bounding Box (Strait of Hormuz)
- Lat: 26.5°N – 26.8°N
- Lon: 56.0°E – 56.5°E
- Map center: [56.3, 26.65], zoom 8
- Bounding box already enforced in `vessel_positions` data via pipeline filters — the map shows all vessels in DB

## Tech Stack Choices
- **Framework**: Next.js 15 App Router (specified in HOR-2 and README)
- **Map**: Mapbox GL JS (specified in HOR-5 description) — requires a free Mapbox token
- **Chart**: Recharts (specified in HOR-5 description — "D3/Recharts")
- **Styles**: Tailwind CSS (specified across multiple issues)
- **DB client**: `pg` (Node.js driver) — NOT asyncpg (Python only), NOT Prisma (overkill for MVP)
- **Deploy**: Vercel (specified in HOR-5 and HOR-2)

## Mapbox GL + Next.js Gotcha
`mapbox-gl` uses browser APIs (`window`, `Worker`) and must ONLY be imported in Client Components (`'use client'`). The HormuzMap component must have `'use client'` at the top. Dynamic import with `ssr: false` is an alternative:
```typescript
const HormuzMap = dynamic(() => import('@/components/HormuzMap'), { ssr: false });
```

## Empty State Handling
The DB may have no vessel_positions or oil_prices data at MVP deploy time (pipelines not yet running against production DB). Both API routes should return empty arrays gracefully. The page should render without errors when data arrays are empty.

## GitHub Repo
- Repo: `Samizdat-Publications/chokepoint`
- Branch: master
- Push `frontend/` after implementation

## HOR-4 Status
HOR-4 (oil prices pipeline) is `in_progress` in Paperclip but was never implemented. The `oil_prices` DB table exists but has no data. The chart's Brent price line will be empty until HOR-4 runs. This is acceptable for MVP — the chart component handles empty data gracefully.
</critical_context>

<current_state>
## HOR-5 Status: Not started

### Deliverable status:
| File | Status |
|------|--------|
| `frontend/` directory | Does not exist |
| `frontend/app/page.tsx` | Not created |
| `frontend/app/layout.tsx` | Not created |
| `frontend/app/api/vessels/latest/route.ts` | Not created |
| `frontend/app/api/chart/daily/route.ts` | Not created |
| `frontend/components/HormuzMap.tsx` | Not created |
| `frontend/components/PriceTransitChart.tsx` | Not created |
| `frontend/lib/db.ts` | Not created |
| `frontend/next.config.ts` | Not created |
| `frontend/.env.local` | Not created (not committed) |
| Vercel deployment | Not done |

### Git state:
- Working tree has one modification: `whats-next.md` (this file, updated this session)
- All other prior work committed at `4585a2a`
- Branch: master

### Next agent action:
Start at Step 1 (scaffold Next.js app with `create-next-app`), work through all steps in order. Steps 1–9 can be done in one session. Steps 10–11 are minor config edits. Step 12 is local dev verification. Step 13 (Vercel deploy) requires the Mapbox token and DATABASE_URL environment variables — check if these are available in the environment before attempting deploy.
</current_state>
