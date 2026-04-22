import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
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
    return NextResponse.json(result.rows);
  } catch {
    return NextResponse.json({ error: 'DB unavailable' }, { status: 503 });
  }
}
