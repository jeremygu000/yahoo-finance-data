"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Box from "@mui/material/Box";
import { useThemeMode } from "./ThemeProvider";
import { useLivePrices } from "./PriceProvider";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Pagination from "@mui/material/Pagination";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import SearchIcon from "@mui/icons-material/Search";
import { fetchTickerOverview } from "@/lib/api";
import type { TickerOverviewItem, TickerOverviewResponse } from "@/lib/types";

const PAGE_SIZE = 24;

function formatPrice(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatVolume(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

const ICON_COLORS = ["#3b89ff", "#ff7134", "#fdbc2a", "#36bb80", "#a855f7", "#ec4899"];

const flashKeyframes = `
  @keyframes priceFlashUp {
    0% { background-color: rgba(54, 187, 128, 0.0); }
    30% { background-color: rgba(54, 187, 128, 0.25); }
    100% { background-color: rgba(54, 187, 128, 0.0); }
  }
  @keyframes priceFlashDown {
    0% { background-color: rgba(255, 113, 52, 0.0); }
    30% { background-color: rgba(255, 113, 52, 0.25); }
    100% { background-color: rgba(255, 113, 52, 0.0); }
  }
`;

function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

export default function TickerOverview() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<TickerOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [softLoading, setSoftLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { mode } = useThemeMode();
  const { prices: livePrices } = useLivePrices();

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasLoadedRef = useRef(false);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
      setPage(1);
    }, 300);
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!hasLoadedRef.current) {
        setLoading(true);
      } else {
        setSoftLoading(true);
      }
      setError(null);

      try {
        const result = await fetchTickerOverview(page, PAGE_SIZE, search);
        if (!cancelled) {
          setData(result);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load");
        }
      } finally {
        if (!cancelled) {
          hasLoadedRef.current = true;
          setLoading(false);
          setSoftLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [page, search]);

  if (loading && !hasLoadedRef.current) {
    return (
      <Box>
        <Box sx={{ mb: 2.5 }}>
          <Skeleton variant="rounded" height={56} sx={{ borderRadius: "8px", maxWidth: 400 }} />
        </Box>
        <Grid container spacing={2}>
          {Array.from({ length: 6 }, (_, i) => (
            <Grid key={`skel-${String(i)}`} size={{ xs: 12, sm: 6, lg: 4 }}>
              <Skeleton variant="rounded" height={160} sx={{ borderRadius: "12px" }} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error && !hasLoadedRef.current) {
    return <Alert severity="error">{error}</Alert>;
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;
  const startIdx = (page - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(page * PAGE_SIZE, total);

  return (
    <>
      <style>{flashKeyframes}</style>

      <Box sx={{ mb: 2.5 }}>
        <TextField
          value={searchInput}
          onChange={handleSearchChange}
          placeholder="Search tickers..."
          size="small"
          sx={{ width: { xs: "100%", sm: 400 } }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: "1.1rem", color: "text.disabled" }} />
                </InputAdornment>
              ),
            },
          }}
        />
      </Box>

      <Box sx={{ opacity: softLoading ? 0.6 : 1, transition: "opacity 0.2s" }}>
        <Grid container spacing={2}>
          {items.map((item, idx) => {
            const liveData = livePrices[item.ticker];
            const displayClose = liveData ? liveData.close : (item.latest?.close ?? null);
            const isLive = liveData !== undefined;
            const isUp = item.change !== null && item.change >= 0;
            const iconColor = ICON_COLORS[idx % ICON_COLORS.length];

            return (
              <TickerCard
                key={item.ticker}
                item={item}
                displayClose={displayClose}
                isLive={isLive}
                isUp={isUp}
                iconColor={iconColor}
                mode={mode}
              />
            );
          })}
        </Grid>
      </Box>

      {total > 0 && (
        <Box
          sx={{
            mt: 3,
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            alignItems: { xs: "flex-start", sm: "center" },
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Typography
            sx={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.75rem",
              color: "text.secondary",
            }}
          >
            Showing {startIdx}–{endIdx} of {total} tickers
          </Typography>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_e, val) => setPage(val)}
            color="primary"
            size="small"
            siblingCount={1}
            boundaryCount={1}
            sx={{
              "& .MuiPaginationItem-root": {
                fontFamily: "var(--font-geist-mono)",
                fontSize: "0.75rem",
              },
            }}
          />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </>
  );
}

interface TickerCardProps {
  item: TickerOverviewItem;
  displayClose: number | null;
  isLive: boolean;
  isUp: boolean;
  iconColor: string;
  mode: "light" | "dark";
}

function TickerCard({ item, displayClose, isLive, isUp, iconColor, mode }: TickerCardProps) {
  const prevClose = usePrevious(displayClose);
  const [flashDir, setFlashDir] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (prevClose !== undefined && displayClose !== null && prevClose !== null && displayClose !== prevClose) {
      const dir = displayClose > prevClose ? "up" : "down";
      setFlashDir(dir);
      const timer = setTimeout(() => setFlashDir(null), 800);
      return () => clearTimeout(timer);
    }
  }, [displayClose, prevClose]);

  const flashAnimation =
    flashDir === "up" ? "priceFlashUp 0.8s ease-out" : flashDir === "down" ? "priceFlashDown 0.8s ease-out" : "none";

  return (
    <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
      <Card
        sx={{
          height: "100%",
          transition: "box-shadow 0.2s",
          animation: flashAnimation,
          "&:hover": {
            boxShadow: mode === "dark" ? "0 4px 16px rgba(59,137,255,0.25)" : "0 4px 16px rgba(59,137,255,0.12)",
          },
        }}
      >
        <CardContent sx={{ p: 2.5 }}>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: "10px",
                  bgcolor: `${iconColor}18`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <ShowChartIcon sx={{ color: iconColor, fontSize: "1.1rem" }} />
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    letterSpacing: "0.06em",
                    color: iconColor,
                    textTransform: "uppercase",
                  }}
                >
                  {item.ticker}
                </Typography>
                {isLive && (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.4,
                      px: 0.75,
                      py: 0.2,
                      borderRadius: "4px",
                      bgcolor: "rgba(54,187,128,0.12)",
                      border: "1px solid rgba(54,187,128,0.3)",
                    }}
                  >
                    <Box
                      sx={{
                        width: 5,
                        height: 5,
                        borderRadius: "50%",
                        bgcolor: "#36bb80",
                        "@keyframes pulse": {
                          "0%, 100%": { opacity: 1 },
                          "50%": { opacity: 0.4 },
                        },
                        animation: "pulse 1.5s ease-in-out infinite",
                      }}
                    />
                    <Typography
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontSize: "0.55rem",
                        fontWeight: 700,
                        color: "#36bb80",
                        letterSpacing: "0.06em",
                      }}
                    >
                      LIVE
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>

            {item.change !== null && (
              <Chip
                icon={
                  isUp ? (
                    <TrendingUpIcon sx={{ fontSize: "0.85rem !important" }} />
                  ) : (
                    <TrendingDownIcon sx={{ fontSize: "0.85rem !important" }} />
                  )
                }
                label={`${isUp ? "+" : ""}${(item.change_pct ?? 0).toFixed(2)}%`}
                size="small"
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontWeight: 700,
                  fontSize: "0.7rem",
                  bgcolor: isUp ? "rgba(54,187,128,0.1)" : "rgba(255,113,52,0.1)",
                  color: isUp ? "#36bb80" : "#ff7134",
                  "& .MuiChip-icon": {
                    color: "inherit",
                  },
                }}
              />
            )}
          </Box>

          <Box sx={{ mb: 2 }}>
            {displayClose !== null ? (
              <Typography
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontWeight: 700,
                  fontSize: "1.75rem",
                  color: flashDir === "up" ? "#36bb80" : flashDir === "down" ? "#ff7134" : "text.primary",
                  lineHeight: 1.1,
                  transition: "color 0.3s ease",
                }}
              >
                {formatPrice(displayClose)}
              </Typography>
            ) : (
              <Typography
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: "1.25rem",
                  color: "text.disabled",
                }}
              >
                —
              </Typography>
            )}
            {item.change !== null && (
              <Typography
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: "0.8rem",
                  color: isUp ? "#36bb80" : "#ff7134",
                  mt: 0.25,
                }}
              >
                {item.change >= 0 ? "+" : ""}
                {formatPrice(item.change)}
              </Typography>
            )}
          </Box>

          <Box
            sx={{
              pt: 1.5,
              borderTop: "1px solid",
              borderColor: "divider",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 0.75,
            }}
          >
            {[
              { label: "Rows", value: item.rows.toLocaleString() },
              { label: "Size", value: `${item.size_kb} KB` },
            ].map((stat) => (
              <Box key={stat.label}>
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.disabled",
                    fontSize: "0.65rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    display: "block",
                  }}
                >
                  {stat.label}
                </Typography>
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                  {stat.value}
                </Typography>
              </Box>
            ))}
            <Box sx={{ gridColumn: "1 / -1" }}>
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  fontSize: "0.65rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  display: "block",
                }}
              >
                Range
              </Typography>
              <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                {item.first_date} → {item.last_date}
              </Typography>
            </Box>
            {item.latest && (
              <Box>
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.disabled",
                    fontSize: "0.65rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    display: "block",
                  }}
                >
                  Volume
                </Typography>
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                  {formatVolume(item.latest.volume)}
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </Grid>
  );
}
