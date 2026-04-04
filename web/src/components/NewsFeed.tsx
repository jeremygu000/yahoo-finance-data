"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import { fetchNews } from "@/lib/api";
import type { NewsResponse, NewsArticle } from "@/lib/types";
import useTickers from "@/lib/useTickers";

// --- Helpers ---

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diffMs = now - timestamp * 1000;
  const diffSecs = Math.floor(diffMs / 1000);
  if (diffSecs < 60) return `${diffSecs}s ago`;
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

// --- Sub-components ---

const SKELETON_KEYS = Array.from({ length: 4 }, (_, i) => `news-sk-${String(i)}`);

interface ArticleCardProps {
  article: NewsArticle;
}

function ArticleCard({ article }: ArticleCardProps) {
  const relTime =
    article.provider_publish_time !== null
      ? formatRelativeTime(article.provider_publish_time)
      : null;

  return (
    <Box
      component="a"
      href={article.link ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      sx={{
        display: "flex",
        gap: 1.5,
        p: 1.75,
        borderRadius: "8px",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "rgba(255,255,255,0.02)",
        textDecoration: "none",
        color: "inherit",
        transition: "background-color 0.15s ease, border-color 0.15s ease",
        "&:hover": {
          bgcolor: "rgba(255,255,255,0.05)",
          borderColor: "rgba(59,137,255,0.35)",
        },
      }}
    >
      {article.thumbnail_url && (
        <Box
          component="img"
          src={article.thumbnail_url}
          alt=""
          sx={{
            width: 72,
            height: 54,
            objectFit: "cover",
            borderRadius: "6px",
            flexShrink: 0,
            bgcolor: "rgba(255,255,255,0.04)",
          }}
        />
      )}

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            lineHeight: 1.4,
            mb: 0.75,
            color: "text.primary",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {article.title ?? "Untitled"}
        </Typography>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          {article.publisher && (
            <Typography
              variant="caption"
              sx={{
                color: "text.disabled",
                fontSize: "0.7rem",
                letterSpacing: "0.03em",
                textTransform: "uppercase",
                fontFamily: "var(--font-geist-mono)",
              }}
            >
              {article.publisher}
            </Typography>
          )}

          {relTime && (
            <>
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.2)", fontSize: "0.65rem" }}>
                ·
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  fontSize: "0.7rem",
                  fontFamily: "var(--font-geist-mono)",
                }}
              >
                {relTime}
              </Typography>
            </>
          )}
        </Box>

        {article.related_tickers && article.related_tickers.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75 }}>
            {article.related_tickers.slice(0, 5).map((t) => (
              <Chip
                key={t}
                label={t}
                size="small"
                sx={{
                  bgcolor: "rgba(59,137,255,0.1)",
                  color: "#3b89ff",
                  borderRadius: "4px",
                  fontSize: "0.62rem",
                  fontFamily: "var(--font-geist-mono)",
                  fontWeight: 600,
                  height: 18,
                  "& .MuiChip-label": { px: 0.75 },
                }}
              />
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}

// --- Main component ---

export default function NewsFeed() {
  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [data, setData] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (tickers.length > 0 && !ticker) setTicker(tickers[0]);
  }, [tickers, ticker]);

  useEffect(() => {
    if (!ticker) return;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchNews(ticker, 20);
        setData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

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
          {!loading && data && (
            <Typography
              variant="caption"
              sx={{ ml: "auto", color: "text.disabled", fontFamily: "var(--font-geist-mono)" }}
            >
              {data.count} articles
            </Typography>
          )}
          <Typography
            variant="caption"
            sx={{ ml: data ? 0 : "auto", color: "text.disabled", fontFamily: "var(--font-geist-mono)" }}
          >
            {data ? null : "News Feed"}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Divider sx={{ mb: 2 }} />

        {loading ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            {SKELETON_KEYS.map((k) => (
              <Box
                key={k}
                sx={{
                  display: "flex",
                  gap: 1.5,
                  p: 1.75,
                  borderRadius: "8px",
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Skeleton variant="rounded" width={72} height={54} sx={{ flexShrink: 0 }} />
                <Box sx={{ flex: 1 }}>
                  <Skeleton variant="text" width="90%" height={20} />
                  <Skeleton variant="text" width="60%" height={20} sx={{ mt: 0.5 }} />
                  <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                    <Skeleton variant="rounded" width={80} height={16} />
                    <Skeleton variant="rounded" width={50} height={16} />
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
        ) : data && data.articles.length > 0 ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
            {data.articles.map((article) => (
              <ArticleCard
                key={article.uuid ?? `${article.title ?? ""}-${article.publisher ?? ""}`}
                article={article}
              />
            ))}
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              py: 6,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: "text.disabled",
                fontFamily: "var(--font-geist-mono)",
                fontSize: "0.8rem",
              }}
            >
              No news available
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
