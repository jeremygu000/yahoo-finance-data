import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";
import TickerOverview from "@/components/TickerOverview";
import CandlestickChart from "@/components/CandlestickChart";
import PriceComparison from "@/components/PriceComparison";
import DataTable from "@/components/DataTable";
import VixDashboard from "@/components/VixDashboard";
import IndicatorChart from "@/components/IndicatorChart";
import AlertManager from "@/components/AlertManager";
import AISummary from "@/components/AISummary";
import FundamentalsCard from "@/components/FundamentalsCard";

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
      <Chip
        label={num}
        size="small"
        sx={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: "0.7rem",
          fontWeight: 700,
          bgcolor: "primary.main",
          color: "white",
          height: 22,
          borderRadius: "6px",
        }}
      />
      <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "1rem", color: "text.primary" }}>
        {title}
      </Typography>
      <Divider sx={{ flex: 1, borderColor: "divider" }} />
    </Box>
  );
}

export default function Home() {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box
        component="main"
        sx={{
          flex: 1,
          overflowY: "auto",
          height: "100vh",
        }}
      >
        <HeroBanner />

        <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5, display: "flex", flexDirection: "column", gap: 6 }}>
          <Box component="section" id="overview" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="01" title="Ticker Overview" />
            <TickerOverview />
          </Box>

          <Box component="section" id="fundamentals" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="02" title="Fundamentals" />
            <FundamentalsCard />
          </Box>

          <Box component="section" id="candlestick" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="03" title="Candlestick Chart" />
            <CandlestickChart />
          </Box>

          <Box component="section" id="comparison" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="04" title="Price Comparison" />
            <PriceComparison />
          </Box>

          <Box component="section" id="table" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="05" title="OHLCV Data Table" />
            <DataTable />
          </Box>

          <Box component="section" id="vix" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="06" title="VIX Dashboard" />
            <VixDashboard />
          </Box>

          <Box component="section" id="indicators" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="07" title="Technical Indicators" />
            <IndicatorChart />
          </Box>

          <Box component="section" id="alerts" sx={{ scrollMarginTop: 32 }}>
            <SectionHeader num="08" title="Price Alerts" />
            <AlertManager />
          </Box>

          <Box component="section" id="ai-summary" sx={{ scrollMarginTop: 32, pb: 8 }}>
            <SectionHeader num="09" title="AI Summary" />
            <AISummary />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
