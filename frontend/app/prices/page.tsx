import dynamic from 'next/dynamic';
import pool from '@/lib/db';

const PriceTransitChart = dynamic(() => import('@/components/PriceTransitChart'), { ssr: false });

async function getChartData() {
  try {
    const result = await pool.query(`
      SELECT
        p.day,
        p.brent_price,
        COALESCE(t.vessel_count, 0) AS vessel_count
      FROM (
        SELECT
          time_bucket('1 day', time) AS day,
          AVG(price)                 AS brent_price
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
    return result.rows;
  } catch {
    return [];
  }
}

export default async function PricesPage() {
  const data = await getChartData();

  return (
    <div className="flex flex-col flex-1 p-4 gap-4">
      <div>
        <h1 className="text-sm font-semibold text-gray-300">Brent Crude vs Hormuz Transits</h1>
        <p className="text-xs text-gray-500 mt-1">90-day rolling window</p>
      </div>
      <div className="flex-1 min-h-0">
        <PriceTransitChart data={data} />
      </div>
    </div>
  );
}
