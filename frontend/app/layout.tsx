import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'ChokePoint',
  description: 'Strait of Hormuz tanker intelligence — real-time AIS data correlated with Brent crude prices',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-gray-950 text-gray-100 antialiased">
        <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
          <nav className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-8">
            <Link href="/" className="text-orange-500 font-bold text-lg tracking-tight hover:text-orange-400 transition-colors">
              ChokePoint
            </Link>
            <div className="flex items-center gap-6 text-sm">
              <Link href="/map" className="text-gray-400 hover:text-gray-100 transition-colors">
                Live Map
              </Link>
              <Link href="/prices" className="text-gray-400 hover:text-gray-100 transition-colors">
                Prices
              </Link>
            </div>
          </nav>
        </header>
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
