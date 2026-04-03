import Sidebar from "@/components/Sidebar";
import TickerOverview from "@/components/TickerOverview";
import CandlestickChart from "@/components/CandlestickChart";
import PriceComparison from "@/components/PriceComparison";
import DataTable from "@/components/DataTable";
import VixDashboard from "@/components/VixDashboard";

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="section-header">
      <span className="section-number">{num}</span>
      <h2>{title}</h2>
      <span className="section-divider" />
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="flex-1 ml-56 overflow-y-auto h-screen">
        <div className="max-w-6xl mx-auto px-8 py-8 space-y-16">
          <section id="overview" className="scroll-mt-8">
            <SectionHeader num="01" title="Ticker Overview" />
            <TickerOverview />
          </section>

          <section id="candlestick" className="scroll-mt-8">
            <SectionHeader num="02" title="Candlestick Chart" />
            <CandlestickChart />
          </section>

          <section id="comparison" className="scroll-mt-8">
            <SectionHeader num="03" title="Price Comparison" />
            <PriceComparison />
          </section>

          <section id="table" className="scroll-mt-8">
            <SectionHeader num="04" title="OHLCV Data Table" />
            <DataTable />
          </section>

          <section id="vix" className="scroll-mt-8 pb-16">
            <SectionHeader num="05" title="VIX Dashboard" />
            <VixDashboard />
          </section>
        </div>
      </main>
    </div>
  );
}
