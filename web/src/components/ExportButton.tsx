"use client";

import { useState } from "react";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import DownloadIcon from "@mui/icons-material/Download";
import { getExportUrl } from "@/lib/api";

interface ExportButtonProps {
  ticker: string;
  days?: number;
}

export default function ExportButton({ ticker, days = 365 }: ExportButtonProps) {
  const [downloading, setDownloading] = useState(false);

  function handleExport() {
    setDownloading(true);
    const url = getExportUrl(ticker, days);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ticker}_ohlcv_${days}d.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => setDownloading(false), 1500);
  }

  return (
    <Tooltip title={downloading ? "Downloading…" : `Export ${ticker} CSV`} arrow>
      <Button
        variant="outlined"
        size="small"
        startIcon={<DownloadIcon sx={{ fontSize: "0.85rem !important" }} />}
        onClick={handleExport}
        sx={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: "0.75rem",
          textTransform: "none",
          borderColor: "divider",
          color: "text.secondary",
          height: 30,
          px: 1.25,
          "&:hover": {
            borderColor: "text.disabled",
            color: "text.primary",
            bgcolor: "action.hover",
          },
        }}
      >
        {downloading ? "CSV…" : "CSV"}
      </Button>
    </Tooltip>
  );
}
