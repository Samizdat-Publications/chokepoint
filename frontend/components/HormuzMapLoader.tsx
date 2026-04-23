'use client';
import dynamic from 'next/dynamic';
import type { ComponentProps } from 'react';
import type HormuzMapType from './HormuzMap';

// dynamic import with ssr:false must live in a Client Component (Next.js 16)
const HormuzMap = dynamic(() => import('./HormuzMap'), { ssr: false });

export default function HormuzMapLoader(props: ComponentProps<typeof HormuzMapType>) {
  return <HormuzMap {...props} />;
}
