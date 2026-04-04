"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Divider from "@mui/material/Divider";
import RefreshIcon from "@mui/icons-material/Refresh";
import DeleteIcon from "@mui/icons-material/Delete";
import FolderIcon from "@mui/icons-material/Folder";
import StorageIcon from "@mui/icons-material/Storage";
import TableRowsIcon from "@mui/icons-material/TableRows";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import CleaningServicesIcon from "@mui/icons-material/CleaningServices";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { fetchStorageSummary, fetchDataQuality, cleanData, deleteTickerData } from "@/lib/api";
import type { StorageSummary, QualityReportResponse, TickerQualityItem, AnomalyItem, CleanResponse, SortDirection } from "@/lib/types";

type QualitySortKey = keyof TickerQualityItem;

const SKELETON_KEYS = Array.from({ length: 6 }, (_, i) => `sk-${String(i)}`);

const MONO = "var(--font-geist-mono)";
const GREEN = "#36bb80";
const ORANGE = "#ff7134";
const BLUE = "#3b89ff";

function stalenessColor(days: number): string {
  if (days < 3) return GREEN;
  if (days <= 7) return ORANGE;
  return "#ef4444";
}

function fmtKb(kb: number): string {
  return kb.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function fmtPct(val: number): string {
  return `${val.toFixed(1)}%`;
}

function sortQualityRows(
  rows: TickerQualityItem[],
  col: QualitySortKey,
  dir: SortDirection,
): TickerQualityItem[] {
  return rows.toSorted((a, b) => {
    const av = a[col];
    const bv = b[col];
    if (typeof av === "string" && typeof bv === "string") {
      return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    const an = av as number;
    const bn = bv as number;
    return dir === "asc" ? an - bn : bn - an;
  });
}

export default function DataManagement() {
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [quality, setQuality] = useState<QualityReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [sortCol, setSortCol] = useState<QualitySortKey>("ticker");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");

  const [keepDays, setKeepDays] = useState("365");
  const [cleaning, setCleaning] = useState(false);
  const [cleanError, setCleanError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [s, q] = await Promise.all([fetchStorageSummary(), fetchDataQuality(3)]);
      setSummary(s);
      setQuality(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data management info");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function showSuccess(msg: string) {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  }

  function handleSort(col: QualitySortKey) {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  }

  async function handleClean() {
    const days = parseInt(keepDays, 10);
    if (isNaN(days) || days < 1) {
      setCleanError("Keep days must be a positive integer");
      return;
    }
    if (!window.confirm(`Remove all data older than ${days} days? This cannot be undone.`)) return;
    setCleanError(null);
    setCleaning(true);
    try {
      const result: CleanResponse = await cleanData({ keep_days: days });
      showSuccess(`Cleaned ${result.total_removed} file(s) successfully.`);
      await load();
    } catch (e) {
      setCleanError(e instanceof Error ? e.message : "Failed to clean data");
    } finally {
      setCleaning(false);
    }
  }

  async function handleDeleteTicker(ticker: string) {
    if (!window.confirm(`Delete ALL data files for ${ticker}? This cannot be undone.`)) return;
    try {
      const result = await deleteTickerData(ticker);
      showSuccess(`Deleted ${result.files_removed} file(s) for ${ticker}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to delete ${ticker}`);
    }
  }

  const qualityRows = quality?.tickers ?? [];
  const anomalies: AnomalyItem[] = quality?.anomalies ?? [];
  const sorted = sortQualityRows(qualityRows, sortCol, sortDir);

  const qualityCols: { key: QualitySortKey; label: string; align: "left" | "right" | "center" }[] = [
    { key: "ticker", label: "Ticker", align: "left" },
    { key: "interval", label: "Interval", align: "left" },
    { key: "rows", label: "Rows", align: "right" },
    { key: "first_date", label: "First Date", align: "left" },
    { key: "last_date", label: "Last Date", align: "left" },
    { key: "days_stale", label: "Stale", align: "right" },
    { key: "completeness_pct", label: "Completeness", align: "left" },
    { key: "nan_pct", label: "NaN %", align: "right" },
    { key: "anomalies", label: "Anomalies", align: "right" },
    { key: "outliers", label: "Outliers", align: "right" },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {/* --- Header --- */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "text.primary", mb: 0.5 }}>
            Data Management
          </Typography>
          <Typography variant="body2" sx={{ color: "text.disabled" }}>
            Storage health, quality metrics, and cleanup tools
          </Typography>
        </Box>
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshIcon />}
          onClick={() => void load()}
          disabled={loading}
          sx={{ fontWeight: 600, textTransform: "none", height: 36 }}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 0 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {successMsg && (
        <Alert severity="success" sx={{ mb: 0 }}>
          {successMsg}
        </Alert>
      )}

      {/* --- Storage Summary Cards --- */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2 }}>
        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              <FolderIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Total Files
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <Typography sx={{ fontFamily: MONO, fontSize: "1.5rem", fontWeight: 700, color: "text.primary" }}>
                {summary?.total_files.toLocaleString() ?? "—"}
              </Typography>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              <StorageIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Total Size
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <>
                <Typography sx={{ fontFamily: MONO, fontSize: "1.5rem", fontWeight: 700, color: "text.primary" }}>
                  {summary ? fmtKb(summary.total_size_kb) : "—"}
                  <Typography component="span" sx={{ fontFamily: MONO, fontSize: "0.85rem", color: "text.disabled", ml: 0.5 }}>
                    KB
                  </Typography>
                </Typography>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              <TableRowsIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Total Rows
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <>
                <Typography sx={{ fontFamily: MONO, fontSize: "1.5rem", fontWeight: 700, color: "text.primary" }}>
                  {summary?.total_rows.toLocaleString() ?? "—"}
                </Typography>
                {summary?.oldest_date && (
                  <Typography variant="caption" sx={{ color: "text.disabled", fontFamily: MONO, display: "block", mt: 0.5 }}>
                    {summary.oldest_date} → {summary.newest_date}
                  </Typography>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              <ShowChartIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Tickers
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <Typography sx={{ fontFamily: MONO, fontSize: "1.5rem", fontWeight: 700, color: BLUE }}>
                {summary?.ticker_count.toLocaleString() ?? "—"}
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* --- Ticker Quality Table --- */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Ticker Quality
            </Typography>
            {!loading && quality && (
              <Typography variant="caption" sx={{ color: "text.disabled", fontFamily: MONO }}>
                {qualityRows.length} ticker{qualityRows.length !== 1 ? "s" : ""} · scanned {quality.scan_date}
              </Typography>
            )}
          </Box>

          <TableContainer sx={{ borderRadius: "8px", border: "1px solid", borderColor: "divider" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {qualityCols.map((col) => (
                    <TableCell key={col.key} align={col.align} sortDirection={sortCol === col.key ? sortDir : false}>
                      <TableSortLabel
                        active={sortCol === col.key}
                        direction={sortCol === col.key ? sortDir : "asc"}
                        onClick={() => handleSort(col.key)}
                      >
                        {col.label}
                      </TableSortLabel>
                    </TableCell>
                  ))}
                  <TableCell align="center" sx={{ width: 48 }} />
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  SKELETON_KEYS.map((sk) => (
                    <TableRow key={sk}>
                      {qualityCols.map((col) => (
                        <TableCell key={col.key}>
                          <Skeleton variant="text" width="80%" />
                        </TableCell>
                      ))}
                      <TableCell />
                    </TableRow>
                  ))
                ) : qualityRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={qualityCols.length + 1} align="center" sx={{ py: 4, color: "text.disabled" }}>
                      No data files found.
                    </TableCell>
                  </TableRow>
                ) : (
                  sorted.map((row) => (
                    <TableRow key={`${row.ticker}-${row.interval}`} hover>
                      <TableCell sx={{ fontFamily: MONO, fontWeight: 700, color: "text.primary" }}>
                        {row.ticker}
                      </TableCell>
                      <TableCell sx={{ fontFamily: MONO }}>
                        <Chip
                          label={row.interval}
                          size="small"
                          sx={{
                            fontFamily: MONO,
                            fontSize: "0.7rem",
                            height: 20,
                            bgcolor: "action.hover",
                            color: "text.secondary",
                          }}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: MONO, color: "text.secondary" }}>
                        {row.rows.toLocaleString()}
                      </TableCell>
                      <TableCell sx={{ fontFamily: MONO, color: "text.secondary", fontSize: "0.75rem" }}>
                        {row.first_date}
                      </TableCell>
                      <TableCell sx={{ fontFamily: MONO, color: "text.secondary", fontSize: "0.75rem" }}>
                        {row.last_date}
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          component="span"
                          sx={{
                            fontFamily: MONO,
                            fontWeight: 700,
                            fontSize: "0.8rem",
                            color: stalenessColor(row.days_stale),
                          }}
                        >
                          {row.days_stale}d
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ minWidth: 120 }}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(row.completeness_pct, 100)}
                            sx={{
                              flex: 1,
                              height: 6,
                              borderRadius: 3,
                              bgcolor: "action.hover",
                              "& .MuiLinearProgress-bar": {
                                bgcolor:
                                  row.completeness_pct >= 90
                                    ? GREEN
                                    : row.completeness_pct >= 70
                                      ? ORANGE
                                      : "#ef4444",
                                borderRadius: 3,
                              },
                            }}
                          />
                          <Typography
                            component="span"
                            sx={{ fontFamily: MONO, fontSize: "0.7rem", color: "text.secondary", minWidth: 38 }}
                          >
                            {fmtPct(row.completeness_pct)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: MONO, color: "text.secondary", fontSize: "0.8rem" }}>
                        {fmtPct(row.nan_pct)}
                      </TableCell>
                      <TableCell align="right">
                        {row.anomalies > 0 ? (
                          <Chip
                            label={row.anomalies}
                            size="small"
                            sx={{
                              fontFamily: MONO,
                              fontSize: "0.7rem",
                              height: 20,
                              bgcolor: "rgba(255,113,52,0.15)",
                              color: ORANGE,
                              fontWeight: 700,
                            }}
                          />
                        ) : (
                          <Typography component="span" sx={{ fontFamily: MONO, fontSize: "0.8rem", color: "text.disabled" }}>
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {row.outliers > 0 ? (
                          <Chip
                            label={row.outliers}
                            size="small"
                            sx={{
                              fontFamily: MONO,
                              fontSize: "0.7rem",
                              height: 20,
                              bgcolor: "rgba(59,137,255,0.15)",
                              color: BLUE,
                              fontWeight: 700,
                            }}
                          />
                        ) : (
                          <Typography component="span" sx={{ fontFamily: MONO, fontSize: "0.8rem", color: "text.disabled" }}>
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          onClick={() => void handleDeleteTicker(row.ticker)}
                          sx={{ color: "text.disabled", "&:hover": { color: "#ef4444" } }}
                          aria-label={`Delete ${row.ticker}`}
                        >
                          <DeleteIcon sx={{ fontSize: "1rem" }} />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* --- Anomalies Section --- */}
      {(loading || anomalies.length > 0) && (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
              <WarningAmberIcon sx={{ fontSize: "1rem", color: ORANGE }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
                Anomalies
              </Typography>
              {!loading && (
                <Chip
                  label={anomalies.length}
                  size="small"
                  sx={{ fontFamily: MONO, fontSize: "0.7rem", height: 20, bgcolor: "rgba(255,113,52,0.15)", color: ORANGE, fontWeight: 700 }}
                />
              )}
            </Box>
            <Divider sx={{ mb: 2.5, borderColor: "divider" }} />

            {loading ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} variant="text" width="70%" height={24} />
                ))}
              </Box>
            ) : (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                {anomalies.map((item: AnomalyItem, idx: number) => (
                  <Box
                    key={idx}
                    sx={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 2,
                      p: 1.5,
                      borderRadius: "6px",
                      bgcolor: "rgba(255,113,52,0.06)",
                      border: "1px solid rgba(255,113,52,0.18)",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 80 }}>
                      <Typography sx={{ fontFamily: MONO, fontWeight: 700, fontSize: "0.85rem", color: ORANGE }}>
                        {item.ticker}
                      </Typography>
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ color: "text.primary", fontWeight: 500 }}>
                        {item.issue}
                      </Typography>
                      <Typography variant="caption" sx={{ color: "text.disabled", fontFamily: MONO }}>
                        {item.detail}
                      </Typography>
                    </Box>
                    <Chip
                      label={`×${item.count}`}
                      size="small"
                      sx={{ fontFamily: MONO, fontSize: "0.7rem", height: 20, bgcolor: "rgba(255,113,52,0.15)", color: ORANGE }}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* --- Cleanup Actions --- */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <CleaningServicesIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Clean Old Data
            </Typography>
          </Box>
          <Divider sx={{ mb: 2.5, borderColor: "divider" }} />

          <Typography variant="body2" sx={{ color: "text.disabled", mb: 2 }}>
            Remove data older than a specified number of days. This operation is irreversible.
          </Typography>

          {cleanError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setCleanError(null)}>
              {cleanError}
            </Alert>
          )}

          <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
            <TextField
              label="Keep Days"
              type="number"
              value={keepDays}
              onChange={(e) => setKeepDays(e.target.value)}
              size="small"
              sx={{ width: 140 }}
              inputProps={{ min: 1, step: 1, style: { fontFamily: MONO } }}
              placeholder="365"
            />
            <Button
              variant="contained"
              size="small"
              color="error"
              startIcon={<CleaningServicesIcon />}
              onClick={() => void handleClean()}
              disabled={cleaning || loading}
              sx={{ height: 40, px: 2.5, fontWeight: 600, textTransform: "none" }}
            >
              {cleaning ? "Cleaning..." : "Clean Old Data"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
