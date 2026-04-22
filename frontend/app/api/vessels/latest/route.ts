import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
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
  } catch {
    return NextResponse.json({ error: 'DB unavailable' }, { status: 503 });
  }
}
