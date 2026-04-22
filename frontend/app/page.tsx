import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center px-4">
      <div className="max-w-2xl text-center space-y-6">
        <h1 className="text-4xl font-bold tracking-tight">
          <span className="text-orange-500">ChokePoint</span> Intelligence
        </h1>
        <p className="text-gray-400 text-lg leading-relaxed">
          Real-time AIS vessel tracking through the Strait of Hormuz, correlated with
          Brent crude prices and financial market anomalies.
        </p>
        <div className="flex gap-4 justify-center pt-2">
          <Link
            href="/map"
            className="px-6 py-3 bg-orange-500 hover:bg-orange-400 text-white font-medium rounded-lg transition-colors"
          >
            Live Map
          </Link>
          <Link
            href="/prices"
            className="px-6 py-3 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-gray-100 font-medium rounded-lg transition-colors"
          >
            Price Chart
          </Link>
        </div>
      </div>
    </div>
  );
}
