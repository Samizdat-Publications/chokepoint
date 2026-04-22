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
      const geojson: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: vessels.map((v) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [v.lon, v.lat] },
          properties: {
            mmsi: v.mmsi,
            name: v.vessel_name ?? `MMSI ${v.mmsi}`,
            type: v.vessel_type ?? 'Unknown',
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
            'match',
            ['get', 'type'],
            'VLCC', '#f97316',
            'Suezmax', '#3b82f6',
            /* default */ '#22c55e',
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
