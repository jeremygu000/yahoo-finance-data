"use client";

import { useState, useEffect, useRef } from "react";
import Snackbar from "@mui/material/Snackbar";
import MuiAlert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import { useLivePrices } from "./PriceProvider";
import type { AlertTriggered } from "@/lib/types";

function formatPrice(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function AlertToast() {
  const { alerts } = useLivePrices();
  const [open, setOpen] = useState(false);
  const [currentAlert, setCurrentAlert] = useState<AlertTriggered | null>(null);
  const shownIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (alerts.length === 0) return;

    const latest = alerts[0];
    if (!shownIdsRef.current.has(latest.alert_id)) {
      shownIdsRef.current.add(latest.alert_id);
      setCurrentAlert(latest);
      setOpen(true);
    }
  }, [alerts]);

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === "clickaway") return;
    setOpen(false);
  };

  if (!currentAlert) return null;

  return (
    <Snackbar
      open={open}
      autoHideDuration={5000}
      onClose={handleClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
    >
      <MuiAlert
        onClose={handleClose}
        severity="warning"
        variant="filled"
        sx={{
          fontFamily: "var(--font-geist-mono)",
          minWidth: 300,
          "& .MuiAlert-message": { width: "100%" },
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          <Typography
            sx={{
              fontFamily: "inherit",
              fontWeight: 700,
              fontSize: "0.8rem",
              letterSpacing: "0.06em",
            }}
          >
            🔔 ALERT: {currentAlert.ticker}
          </Typography>
          <Typography sx={{ fontFamily: "inherit", fontSize: "0.75rem" }}>
            {currentAlert.message}
          </Typography>
          <Box sx={{ display: "flex", gap: 2, mt: 0.5 }}>
            <Box>
              <Typography sx={{ fontFamily: "inherit", fontSize: "0.65rem", opacity: 0.8, textTransform: "uppercase" }}>
                Condition
              </Typography>
              <Typography sx={{ fontFamily: "inherit", fontSize: "0.75rem", fontWeight: 600 }}>
                {currentAlert.condition} {formatPrice(currentAlert.threshold)}
              </Typography>
            </Box>
            <Box>
              <Typography sx={{ fontFamily: "inherit", fontSize: "0.65rem", opacity: 0.8, textTransform: "uppercase" }}>
                Current
              </Typography>
              <Typography sx={{ fontFamily: "inherit", fontSize: "0.75rem", fontWeight: 600 }}>
                {formatPrice(currentAlert.current_price)}
              </Typography>
            </Box>
          </Box>
        </Box>
      </MuiAlert>
    </Snackbar>
  );
}
