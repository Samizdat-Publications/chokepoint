import HormuzMapLoader from '@/components/HormuzMapLoader';
import pool from '@/lib/db';

async function getVessels() {
  try {
    const result = await pool.query(`
      SELECT DISTINCT ON (mmsi) mmsi, vessel_name, vessel_type, lat, lon, speed
      FROM vessel_positions
      WHERE time > NOW() - INTERVAL '2 hours'
        AND vessel_type IN ('VLCC', 'Suezmax', 'Tanker')
      ORDER BY mmsi, time DESC
    `);
    return result.rows;
  } catch {
    return [];
  }
}

export default async function MapPage() {
  const vessels = await getVessels();

  return (
    <div className="flex flex-col flex-1">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h1 className="text-sm font-semibold text-gray-300">
          Strait of Hormuz — Live Vessel Positions
        </h1>
        <span className="text-xs text-gray-500">{vessels.length} vessels tracked</span>
      </div>
      <div className="flex-1">
        <HormuzMapLoader vessels={vessels} />
      </div>
    </div>
  );
}
