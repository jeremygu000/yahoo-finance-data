import Box from "@mui/material/Box";
import Sidebar from "@/components/Sidebar";
import DataManagement from "@/components/DataManagement";

export default function DataManagementPage() {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5 }}>
          <DataManagement />
        </Box>
      </Box>
    </Box>
  );
}
