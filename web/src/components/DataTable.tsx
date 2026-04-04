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
import TablePagination from "@mui/material/TablePagination";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import { fetchOHLCV } from "@/lib/api";
import type { OHLCVBar, SortColumn, SortDirection } from "@/lib/types";
import useTickers from "@/lib/useTickers";

const PAGE_SIZE = 50;
const SKELETON_KEYS = Array.from({ length: 10 }, (_, i) => `skeleton-${String(i)}`);

function formatNum(n: number, decimals = 2): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatVolume(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export default function DataTable() {
  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [allData, setAllData] = useState<OHLCVBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<SortColumn>("date");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");
  const [page, setPage] = useState(0);

  useEffect(() => {
    if (tickers.length > 0 && !ticker) setTicker(tickers[0]);
  }, [tickers, ticker]);

  useEffect(() => {
    if (!ticker) return;
    async function load() {
      setLoading(true);
      setError(null);
      setPage(0);
      try {
        const bars = await fetchOHLCV(ticker, 365);
        setAllData(bars);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  function handleSort(col: SortColumn) {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
    setPage(0);
  }

  const sorted = allData.toSorted((a, b) => {
    let av: string | number, bv: string | number;
    if (sortCol === "date") {
      av = a.date;
      bv = b.date;
    } else {
      av = a[sortCol];
      bv = b[sortCol];
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const totalRows = sorted.length;
  const pageData = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const cols: { key: SortColumn; label: string; align: "left" | "right" }[] = [
    { key: "date", label: "Date", align: "left" },
    { key: "open", label: "Open", align: "right" },
    { key: "high", label: "High", align: "right" },
    { key: "low", label: "Low", align: "right" },
    { key: "close", label: "Close", align: "right" },
    { key: "volume", label: "Volume", align: "right" },
  ];

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
          <Autocomplete
            size="small"
            options={tickers}
            value={ticker}
            onChange={(_, v) => { if (v) setTicker(v); }}
            disableClearable
            sx={{ minWidth: 140 }}
            renderInput={(params) => <TextField {...params} label="Ticker" />}
          />
          {!loading && (
            <Typography
              variant="caption"
              sx={{ ml: "auto", color: "text.disabled", fontFamily: "var(--font-geist-mono)" }}
            >
              {totalRows.toLocaleString()} rows
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
              </TableRow>
            </TableHead>
            <TableBody>
              {loading
                ? SKELETON_KEYS.map((sk) => (
                    <TableRow key={sk}>
                      {cols.map((col) => (
                        <TableCell key={col.key}>
                          <Skeleton variant="text" width="80%" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                : pageData.map((row) => {
                    const isUp = row.close >= row.open;
                    return (
                      <TableRow key={row.date} hover>
                        <TableCell sx={{ fontFamily: "var(--font-geist-mono)", color: "text.secondary" }}>
                          {row.date}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "var(--font-geist-mono)", color: "text.primary" }}>
                          {formatNum(row.open)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "var(--font-geist-mono)", color: "#36bb80" }}>
                          {formatNum(row.high)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "var(--font-geist-mono)", color: "#ff7134" }}>
                          {formatNum(row.low)}
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            fontFamily: "var(--font-geist-mono)",
                            fontWeight: 600,
                            color: isUp ? "#36bb80" : "#ff7134",
                          }}
                        >
                          {formatNum(row.close)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "var(--font-geist-mono)", color: "text.disabled" }}>
                          {formatVolume(row.volume)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
            </TableBody>
          </Table>
        </TableContainer>

        {!loading && totalRows > PAGE_SIZE && (
          <TablePagination
            component="div"
            count={totalRows}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={PAGE_SIZE}
            rowsPerPageOptions={[PAGE_SIZE]}
            sx={{
              borderTop: "1px solid",
              borderColor: "divider",
              mt: 0,
              "& .MuiTablePagination-toolbar": { minHeight: 44 },
              "& .MuiTablePagination-displayedRows": {
                fontFamily: "var(--font-geist-mono)",
                fontSize: "0.8rem",
                color: "text.secondary",
              },
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}
