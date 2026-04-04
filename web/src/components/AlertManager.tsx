"use client";

import { useState, useEffect, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Divider from "@mui/material/Divider";
import NotificationsIcon from "@mui/icons-material/Notifications";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SendIcon from "@mui/icons-material/Send";
import AddIcon from "@mui/icons-material/Add";

import { fetchAlerts, createAlert, deleteAlert, fetchAlertChannels, testAlertNotification } from "@/lib/api";
import type { AlertResponse, AlertCondition } from "@/lib/types";

const CONDITION_OPTIONS: { value: AlertCondition; label: string }[] = [
  { value: "above", label: "Price Above" },
  { value: "below", label: "Price Below" },
  { value: "percent_change_above", label: "% Change Above" },
  { value: "percent_change_below", label: "% Change Below" },
];

function conditionColor(condition: string): string {
  if (condition === "above") return "#36bb80";
  if (condition === "below") return "#ff7134";
  if (condition.startsWith("percent_change")) return "#3b89ff";
  return "#aaa";
}

function conditionLabel(condition: string): string {
  const found = CONDITION_OPTIONS.find((o) => o.value === condition);
  return found ? found.label : condition;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

interface FormState {
  ticker: string;
  condition: AlertCondition;
  threshold: string;
  cooldown: string;
  channels: string[];
  telegramChatId: string;
  email: string;
}

const DEFAULT_FORM: FormState = {
  ticker: "",
  condition: "above",
  threshold: "",
  cooldown: "300",
  channels: [],
  telegramChatId: "",
  email: "",
};

export default function AlertManager() {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [channels, setChannels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" | "info" }>({
    open: false,
    message: "",
    severity: "success",
  });

  const showSnack = (message: string, severity: "success" | "error" | "info" = "success") => {
    setSnackbar({ open: true, message, severity });
  };

  const loadAlerts = useCallback(async () => {
    try {
      const data = await fetchAlerts();
      setAlerts(data.alerts);
    } catch {
      showSnack("Failed to load alerts", "error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchAlerts(), fetchAlertChannels()])
      .then(([alertData, channelData]) => {
        if (!cancelled) {
          setAlerts(alertData.alerts);
          setChannels(channelData);
        }
      })
      .catch(() => {
        if (!cancelled) showSnack("Failed to load alert data", "error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleChannelToggle = (channel: string) => {
    setForm((prev) => ({
      ...prev,
      channels: prev.channels.includes(channel)
        ? prev.channels.filter((c) => c !== channel)
        : [...prev.channels, channel],
    }));
  };

  const handleCreate = async () => {
    if (!form.ticker.trim()) {
      showSnack("Ticker is required", "error");
      return;
    }
    const threshold = parseFloat(form.threshold);
    if (isNaN(threshold)) {
      showSnack("Threshold must be a number", "error");
      return;
    }
    setSubmitting(true);
    try {
      await createAlert({
        ticker: form.ticker.trim().toUpperCase(),
        condition: form.condition,
        threshold,
        cooldown_seconds: parseInt(form.cooldown, 10) || 300,
        channels: form.channels.length > 0 ? form.channels : undefined,
        telegram_chat_id: form.channels.includes("telegram") ? form.telegramChatId : undefined,
        email: form.channels.includes("email") ? form.email : undefined,
      });
      setForm(DEFAULT_FORM);
      await loadAlerts();
      showSnack("Alert created successfully");
    } catch {
      showSnack("Failed to create alert", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (alertId: string) => {
    setDeletingId(alertId);
    try {
      const data = await deleteAlert(alertId);
      setAlerts(data.alerts);
      showSnack("Alert deleted");
    } catch {
      showSnack("Failed to delete alert", "error");
    } finally {
      setDeletingId(null);
    }
  };

  const handleTest = async (alertId: string) => {
    setTestingId(alertId);
    try {
      const result = await testAlertNotification(alertId);
      showSnack(`Test sent — status: ${result.status}`, "info");
    } catch {
      showSnack("Test notification failed", "error");
    } finally {
      setTestingId(null);
    }
  };

  const cardSx = {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "divider",
    borderRadius: "12px",
    p: 2.5,
  };

  const alertCardSx = {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "divider",
    borderRadius: "10px",
    p: 2,
    display: "flex",
    alignItems: "flex-start",
    gap: 2,
    transition: "border-color 0.2s ease",
    "&:hover": {
      borderColor: "rgba(59,137,255,0.3)",
    },
  };

  const labelSx = {
    fontSize: "0.65rem",
    fontFamily: "var(--font-geist-mono)",
    color: "text.secondary",
    textTransform: "uppercase" as const,
    letterSpacing: "0.08em",
    fontWeight: 600,
    mb: 0.5,
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={cardSx}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2.5 }}>
          <Badge badgeContent={alerts.length} color="primary" max={99}>
            <NotificationsIcon sx={{ color: "#3b89ff", fontSize: "1.3rem" }} />
          </Badge>
          <Typography
            sx={{
              fontFamily: "var(--font-geist-sans)",
              fontWeight: 700,
              fontSize: "0.95rem",
              color: "text.primary",
            }}
          >
            Create Price Alert
          </Typography>
        </Box>

        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 2, mb: 2 }}>
          <TextField
            label="Ticker"
            size="small"
            value={form.ticker}
            onChange={(e) => setForm((p) => ({ ...p, ticker: e.target.value.toUpperCase() }))}
            placeholder="AAPL"
            inputProps={{ style: { fontFamily: "var(--font-geist-mono)", fontWeight: 600, fontSize: "0.875rem" } }}
          />

          <FormControl size="small">
            <InputLabel>Condition</InputLabel>
            <Select
              label="Condition"
              value={form.condition}
              onChange={(e) => setForm((p) => ({ ...p, condition: e.target.value as AlertCondition }))}
            >
              {CONDITION_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value} sx={{ fontSize: "0.875rem" }}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Threshold"
            size="small"
            type="number"
            value={form.threshold}
            onChange={(e) => setForm((p) => ({ ...p, threshold: e.target.value }))}
            placeholder="200.00"
            inputProps={{ style: { fontFamily: "var(--font-geist-mono)", fontSize: "0.875rem" } }}
          />

          <TextField
            label="Cooldown (s)"
            size="small"
            type="number"
            value={form.cooldown}
            onChange={(e) => setForm((p) => ({ ...p, cooldown: e.target.value }))}
            inputProps={{ style: { fontFamily: "var(--font-geist-mono)", fontSize: "0.875rem" } }}
          />
        </Box>

        {channels.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography sx={labelSx}>Notification Channels</Typography>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center" }}>
              {channels.map((ch) => (
                <FormControlLabel
                  key={ch}
                  control={
                    <Checkbox
                      size="small"
                      checked={form.channels.includes(ch)}
                      onChange={() => handleChannelToggle(ch)}
                      sx={{
                        color: ch === "telegram" ? "#3b89ff" : "#ff7134",
                        "&.Mui-checked": { color: ch === "telegram" ? "#3b89ff" : "#ff7134" },
                      }}
                    />
                  }
                  label={
                    <Typography sx={{ fontSize: "0.875rem", fontFamily: "var(--font-geist-sans)", textTransform: "capitalize" }}>
                      {ch}
                    </Typography>
                  }
                />
              ))}
            </Box>
          </Box>
        )}

        {form.channels.includes("telegram") && (
          <Box sx={{ mb: 2 }}>
            <TextField
              label="Telegram Chat ID"
              size="small"
              fullWidth
              value={form.telegramChatId}
              onChange={(e) => setForm((p) => ({ ...p, telegramChatId: e.target.value }))}
              placeholder="-1001234567890"
              inputProps={{ style: { fontFamily: "var(--font-geist-mono)", fontSize: "0.875rem" } }}
            />
          </Box>
        )}

        {form.channels.includes("email") && (
          <Box sx={{ mb: 2 }}>
            <TextField
              label="Email Address"
              size="small"
              fullWidth
              type="email"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              placeholder="you@example.com"
              inputProps={{ style: { fontFamily: "var(--font-geist-mono)", fontSize: "0.875rem" } }}
            />
          </Box>
        )}

        <Button
          variant="contained"
          startIcon={submitting ? <CircularProgress size={14} color="inherit" /> : <AddIcon />}
          onClick={handleCreate}
          disabled={submitting}
          sx={{
            bgcolor: "#3b89ff",
            "&:hover": { bgcolor: "#2a78ee" },
            borderRadius: "8px",
            fontFamily: "var(--font-geist-sans)",
            fontWeight: 600,
            fontSize: "0.875rem",
            px: 2.5,
            textTransform: "none",
          }}
        >
          {submitting ? "Creating..." : "Create Alert"}
        </Button>
      </Box>

      <Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
          <Typography
            sx={{
              fontFamily: "var(--font-geist-sans)",
              fontWeight: 600,
              fontSize: "0.875rem",
              color: "text.secondary",
            }}
          >
            Active Alerts
          </Typography>
          <Chip
            label={alerts.length}
            size="small"
            sx={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.7rem",
              fontWeight: 700,
              height: 20,
              bgcolor: "rgba(59,137,255,0.15)",
              color: "#3b89ff",
              border: "1px solid rgba(59,137,255,0.3)",
            }}
          />
          <Divider sx={{ flex: 1, borderColor: "divider" }} />
        </Box>

        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={28} sx={{ color: "#3b89ff" }} />
          </Box>
        )}

        {!loading && alerts.length === 0 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              py: 5,
              gap: 1.5,
              bgcolor: "background.paper",
              border: "1px dashed",
              borderColor: "divider",
              borderRadius: "12px",
            }}
          >
            <NotificationsIcon sx={{ fontSize: "2rem", color: "text.disabled" }} />
            <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.8rem", color: "text.disabled" }}>
              No alerts configured
            </Typography>
            <Typography sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.75rem", color: "text.disabled" }}>
              Create an alert above to get notified when prices move
            </Typography>
          </Box>
        )}

        {!loading && alerts.length > 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            {alerts.map((alert) => (
              <Box key={alert.id} sx={alertCardSx}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1, flexWrap: "wrap" }}>
                    <Typography
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontWeight: 700,
                        fontSize: "0.95rem",
                        color: "text.primary",
                      }}
                    >
                      {alert.ticker}
                    </Typography>
                    <Chip
                      label={conditionLabel(alert.condition)}
                      size="small"
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontSize: "0.65rem",
                        fontWeight: 600,
                        height: 20,
                        bgcolor: `${conditionColor(alert.condition)}18`,
                        color: conditionColor(alert.condition),
                        border: `1px solid ${conditionColor(alert.condition)}44`,
                      }}
                    />
                    <Typography
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontSize: "0.875rem",
                        fontWeight: 600,
                        color: conditionColor(alert.condition),
                      }}
                    >
                      {alert.condition.startsWith("percent_change") ? `${alert.threshold}%` : `$${alert.threshold.toLocaleString()}`}
                    </Typography>
                    {alert.channels.map((ch) => (
                      <Chip
                        key={ch}
                        label={ch}
                        size="small"
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.6rem",
                          fontWeight: 600,
                          height: 18,
                          textTransform: "capitalize",
                          bgcolor: ch === "telegram" ? "rgba(59,137,255,0.12)" : "rgba(255,113,52,0.12)",
                          color: ch === "telegram" ? "#3b89ff" : "#ff7134",
                          border: `1px solid ${ch === "telegram" ? "rgba(59,137,255,0.3)" : "rgba(255,113,52,0.3)"}`,
                        }}
                      />
                    ))}
                  </Box>
                  <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                    <Box>
                      <Typography sx={labelSx}>Created</Typography>
                      <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                        {formatDate(alert.created_at)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography sx={labelSx}>Last Triggered</Typography>
                      <Typography
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.75rem",
                          color: alert.last_triggered ? "#36bb80" : "text.disabled",
                        }}
                      >
                        {formatDate(alert.last_triggered)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography sx={labelSx}>Cooldown</Typography>
                      <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                        {alert.cooldown_seconds}s
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                <Box sx={{ display: "flex", gap: 0.5, flexShrink: 0 }}>
                  <IconButton
                    size="small"
                    onClick={() => handleTest(alert.id)}
                    disabled={testingId === alert.id}
                    title="Test notification"
                    sx={{
                      color: "text.secondary",
                      "&:hover": { color: "#36bb80", bgcolor: "rgba(54,187,128,0.1)" },
                    }}
                  >
                    {testingId === alert.id ? (
                      <CircularProgress size={16} sx={{ color: "#36bb80" }} />
                    ) : (
                      <SendIcon sx={{ fontSize: "1rem" }} />
                    )}
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(alert.id)}
                    disabled={deletingId === alert.id}
                    title="Delete alert"
                    sx={{
                      color: "text.secondary",
                      "&:hover": { color: "#ff7134", bgcolor: "rgba(255,113,52,0.1)" },
                    }}
                  >
                    {deletingId === alert.id ? (
                      <CircularProgress size={16} sx={{ color: "#ff7134" }} />
                    ) : (
                      <DeleteOutlineIcon sx={{ fontSize: "1rem" }} />
                    )}
                  </IconButton>
                </Box>
              </Box>
            ))}
          </Box>
        )}
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.875rem" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
