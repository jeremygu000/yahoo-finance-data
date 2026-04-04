"use client";

import { useEffect, useState, useRef } from "react";
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
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import { fetchTickers, fetchLatest } from "@/lib/api";
import type { TickerInfo, LatestQuote } from "@/lib/types";
import { TICKERS } from "@/lib/types";

interface TickerCard extends TickerInfo {
  latest: LatestQuote | null;
  change: number | null;
  changePct: number | null;
}

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
  const [cards, setCards] = useState<TickerCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { mode } = useThemeMode();
  const { prices: livePrices } = useLivePrices();

  useEffect(() => {
    async function load() {
      try {
        const infos = await fetchTickers();
        const enriched = await Promise.all(
          infos.map(async (info) => {
            const latest = await fetchLatest(info.ticker);
            let change: number | null = null;
            let changePct: number | null = null;
            if (latest) {
              change = latest.close - latest.open;
              changePct = ((latest.close - latest.open) / latest.open) * 100;
            }
            return Object.assign({}, info, { latest, change, changePct });
          }),
        );
        setCards(enriched);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <Grid container spacing={2}>
        {TICKERS.map((t) => (
          <Grid key={t} size={{ xs: 12, sm: 6, lg: 4 }}>
            <Skeleton variant="rounded" height={160} sx={{ borderRadius: "12px" }} />
          </Grid>
        ))}
      </Grid>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <>
      <style>{flashKeyframes}</style>
      <Grid container spacing={2}>
        {cards.map((card, idx) => {
          const liveData = livePrices[card.ticker];
          const displayClose = liveData ? liveData.close : (card.latest?.close ?? null);
          const isLive = liveData !== undefined;

          const isUp = card.change !== null && card.change >= 0;
          const iconColor = ICON_COLORS[idx % ICON_COLORS.length];

          return (
            <TickerCard
              key={card.ticker}
              card={card}
              displayClose={displayClose}
              isLive={isLive}
              isUp={isUp}
              iconColor={iconColor}
              mode={mode}
            />
          );
        })}
      </Grid>
    </>
  );
}

interface TickerCardProps {
  card: TickerCard;
  displayClose: number | null;
  isLive: boolean;
  isUp: boolean;
  iconColor: string;
  mode: "light" | "dark";
}

function TickerCard({ card, displayClose, isLive, isUp, iconColor, mode }: TickerCardProps) {
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
    flashDir === "up"
      ? "priceFlashUp 0.8s ease-out"
      : flashDir === "down"
        ? "priceFlashDown 0.8s ease-out"
        : "none";

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
                  {card.ticker}
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

            {card.change !== null && (
              <Chip
                icon={
                  isUp ? (
                    <TrendingUpIcon sx={{ fontSize: "0.85rem !important" }} />
                  ) : (
                    <TrendingDownIcon sx={{ fontSize: "0.85rem !important" }} />
                  )
                }
                label={`${isUp ? "+" : ""}${(card.changePct ?? 0).toFixed(2)}%`}
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
            {card.change !== null && (
              <Typography
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: "0.8rem",
                  color: isUp ? "#36bb80" : "#ff7134",
                  mt: 0.25,
                }}
              >
                {card.change >= 0 ? "+" : ""}
                {formatPrice(card.change)}
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
              { label: "Rows", value: card.rows.toLocaleString() },
              { label: "Size", value: `${card.size_kb} KB` },
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
                <Typography
                  sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}
                >
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
              <Typography
                sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}
              >
                {card.first_date} → {card.last_date}
              </Typography>
            </Box>
            {card.latest && (
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
                <Typography
                  sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}
                >
                  {formatVolume(card.latest.volume)}
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </Grid>
  );
}
