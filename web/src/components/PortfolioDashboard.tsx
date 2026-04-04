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
import Divider from "@mui/material/Divider";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import { fetchPortfolioSummary, addHolding, deleteHolding } from "@/lib/api";
import type { PortfolioSummaryItem, SortDirection } from "@/lib/types";

type SortKey = "ticker" | "shares" | "avg_cost" | "current_price" | "market_value" | "total_gain" | "gain_pct";

const SKELETON_KEYS = Array.from({ length: 5 }, (_, i) => `sk-${String(i)}`);

const MONO = "var(--font-geist-mono)";
const GREEN = "#36bb80";
const ORANGE = "#ff7134";

function fmtCurrency(val: number | null): string {
  if (val === null) return "N/A";
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function fmtPct(val: number | null): string {
  if (val === null) return "N/A";
  const sign = val >= 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}%`;
}

function fmtShares(val: number): string {
  return val.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

function gainColor(val: number | null): string | undefined {
  if (val === null) return undefined;
  return val >= 0 ? GREEN : ORANGE;
}

function sortRows(rows: PortfolioSummaryItem[], col: SortKey, dir: SortDirection): PortfolioSummaryItem[] {
  return rows.toSorted((a, b) => {
    const av = a[col] ?? (dir === "asc" ? Infinity : -Infinity);
    const bv = b[col] ?? (dir === "asc" ? Infinity : -Infinity);
    if (typeof av === "string" && typeof bv === "string") {
      return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    const an = av as number;
    const bn = bv as number;
    return dir === "asc" ? an - bn : bn - an;
  });
}

export default function PortfolioDashboard() {
  const [rows, setRows] = useState<PortfolioSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<SortKey>("ticker");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");

  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPortfolioSummary();
      setRows(data.holdings);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function handleSort(col: SortKey) {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  }

  async function handleAdd() {
    setAddError(null);
    const trimmedTicker = ticker.trim().toUpperCase();
    const sharesNum = parseFloat(shares);
    const avgCostNum = parseFloat(avgCost);

    if (!trimmedTicker) {
      setAddError("Ticker is required");
      return;
    }
    if (!shares || isNaN(sharesNum) || sharesNum <= 0) {
      setAddError("Shares must be a positive number");
      return;
    }
    if (!avgCost || isNaN(avgCostNum) || avgCostNum <= 0) {
      setAddError("Avg cost must be a positive number");
      return;
    }

    setAdding(true);
    try {
      await addHolding({ ticker: trimmedTicker, shares: sharesNum, avg_cost: avgCostNum });
      setTicker("");
      setShares("");
      setAvgCost("");
      await load();
    } catch (e) {
      setAddError(e instanceof Error ? e.message : "Failed to add holding");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(t: string) {
    if (!window.confirm(`Remove ${t} from your portfolio?`)) return;
    try {
      await deleteHolding(t);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to delete ${t}`);
    }
  }

  const totalValue = rows.reduce((acc, r) => acc + (r.market_value ?? 0), 0);
  const totalGain = rows.reduce((acc, r) => acc + (r.total_gain ?? 0), 0);
  const totalCost = rows.reduce((acc, r) => acc + r.avg_cost * r.shares, 0);
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

  const sorted = sortRows(rows, sortCol, sortDir);

  const cols: { key: SortKey; label: string; align: "left" | "right" }[] = [
    { key: "ticker", label: "Ticker", align: "left" },
    { key: "shares", label: "Shares", align: "right" },
    { key: "avg_cost", label: "Avg Cost", align: "right" },
    { key: "current_price", label: "Current Price", align: "right" },
    { key: "market_value", label: "Market Value", align: "right" },
    { key: "total_gain", label: "Gain / Loss", align: "right" },
    { key: "gain_pct", label: "Gain %", align: "right" },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 700, color: "text.primary", mb: 0.5 }}>
          Portfolio
        </Typography>
        <Typography variant="body2" sx={{ color: "text.disabled" }}>
          Track your holdings and live P&L
        </Typography>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2 }}>
        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              <AccountBalanceWalletIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Total Value
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <Typography sx={{ fontFamily: MONO, fontSize: "1.5rem", fontWeight: 700, color: "text.primary" }}>
                {fmtCurrency(totalValue)}
              </Typography>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              {totalGain >= 0 ? (
                <TrendingUpIcon sx={{ fontSize: "1rem", color: GREEN }} />
              ) : (
                <TrendingDownIcon sx={{ fontSize: "1rem", color: ORANGE }} />
              )}
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Total Gain / Loss
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <Typography
                sx={{
                  fontFamily: MONO,
                  fontSize: "1.5rem",
                  fontWeight: 700,
                  color: gainColor(totalGain) ?? "text.primary",
                }}
              >
                {fmtCurrency(totalGain)}
              </Typography>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
              {totalGainPct >= 0 ? (
                <TrendingUpIcon sx={{ fontSize: "1rem", color: GREEN }} />
              ) : (
                <TrendingDownIcon sx={{ fontSize: "1rem", color: ORANGE }} />
              )}
              <Typography
                variant="caption"
                sx={{ color: "text.disabled", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Return %
              </Typography>
            </Box>
            {loading ? (
              <Skeleton variant="text" width="60%" height={40} />
            ) : (
              <Typography
                sx={{
                  fontFamily: MONO,
                  fontSize: "1.5rem",
                  fontWeight: 700,
                  color: gainColor(totalGainPct) ?? "text.primary",
                }}
              >
                {fmtPct(totalGainPct)}
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Holdings
            </Typography>
            {!loading && (
              <Typography variant="caption" sx={{ color: "text.disabled", fontFamily: MONO }}>
                {rows.length} position{rows.length !== 1 ? "s" : ""}
              </Typography>
            )}
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <TableContainer sx={{ borderRadius: "8px", border: "1px solid", borderColor: "divider" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {cols.map((col) => (
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
                      {cols.map((col) => (
                        <TableCell key={col.key}>
                          <Skeleton variant="text" width="80%" />
                        </TableCell>
                      ))}
                      <TableCell />
                    </TableRow>
                  ))
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={cols.length + 1} align="center" sx={{ py: 4, color: "text.disabled" }}>
                      No holdings yet. Add your first position below.
                    </TableCell>
                  </TableRow>
                ) : (
                  sorted.map((row) => (
                    <TableRow key={row.ticker} hover>
                      <TableCell sx={{ fontFamily: MONO, fontWeight: 700, color: "text.primary" }}>
                        {row.ticker}
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: MONO, color: "text.secondary" }}>
                        {fmtShares(row.shares)}
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: MONO, color: "text.secondary" }}>
                        {fmtCurrency(row.avg_cost)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: MONO, color: row.current_price === null ? "text.disabled" : "text.primary" }}
                      >
                        {row.current_price === null ? "N/A" : fmtCurrency(row.current_price)}
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: MONO, fontWeight: 600, color: "text.primary" }}>
                        {row.market_value === null ? (
                          <Typography component="span" sx={{ color: "text.disabled", fontFamily: MONO }}>
                            N/A
                          </Typography>
                        ) : (
                          fmtCurrency(row.market_value)
                        )}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: MONO, fontWeight: 600, color: gainColor(row.total_gain) ?? "text.disabled" }}
                      >
                        {row.total_gain === null ? "N/A" : fmtCurrency(row.total_gain)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: MONO, fontWeight: 600, color: gainColor(row.gain_pct) ?? "text.disabled" }}
                      >
                        {fmtPct(row.gain_pct)}
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          onClick={() => void handleDelete(row.ticker)}
                          sx={{ color: "text.disabled", "&:hover": { color: ORANGE } }}
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

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary", mb: 2 }}>
            Add Holding
          </Typography>
          <Divider sx={{ mb: 2.5, borderColor: "divider" }} />

          {addError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setAddError(null)}>
              {addError}
            </Alert>
          )}

          <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
            <TextField
              label="Ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              size="small"
              sx={{ width: 120 }}
              inputProps={{ style: { fontFamily: MONO, textTransform: "uppercase" } }}
              placeholder="AAPL"
            />
            <TextField
              label="Shares"
              type="number"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              size="small"
              sx={{ width: 140 }}
              inputProps={{ min: 0, step: "any", style: { fontFamily: MONO } }}
              placeholder="10"
            />
            <TextField
              label="Avg Cost"
              type="number"
              value={avgCost}
              onChange={(e) => setAvgCost(e.target.value)}
              size="small"
              sx={{ width: 160 }}
              inputProps={{ min: 0, step: "any", style: { fontFamily: MONO } }}
              placeholder="150.00"
            />
            <Button
              variant="contained"
              size="small"
              startIcon={<AddIcon />}
              onClick={() => void handleAdd()}
              disabled={adding}
              sx={{ height: 40, px: 2.5, fontWeight: 600, textTransform: "none" }}
            >
              {adding ? "Adding..." : "Add"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
