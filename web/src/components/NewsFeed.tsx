"use client";

import { useEffect, useState, useCallback } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
/** Inline SVG placeholder for articles without a thumbnail. */
const NEWS_PLACEHOLDER_SVG = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="54" fill="none">' +
    '<rect width="72" height="54" rx="6" fill="#161b22"/>' +
    '<rect x="14" y="12" width="20" height="14" rx="2" fill="#484f58"/>' +
    '<rect x="38" y="12" width="20" height="3" rx="1.5" fill="#484f58"/>' +
    '<rect x="38" y="19" width="16" height="3" rx="1.5" fill="#383d44"/>' +
    '<rect x="38" y="26" width="20" height="3" rx="1.5" fill="#383d44"/>' +
    '<rect x="14" y="32" width="44" height="3" rx="1.5" fill="#383d44"/>' +
    '<rect x="14" y="39" width="36" height="3" rx="1.5" fill="#383d44"/>' +
  "</svg>",
)}`;
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

function formatAbsoluteTime(timestamp: number): string {
  const d = new Date(timestamp * 1000);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

// --- Sub-components ---

const SKELETON_KEYS = Array.from({ length: 4 }, (_, i) => `news-sk-${String(i)}`);

interface ArticleCardProps {
  article: NewsArticle;
  onClick: () => void;
}

function ArticleCard({ article, onClick }: ArticleCardProps) {
  const relTime =
    article.provider_publish_time !== null
      ? formatRelativeTime(article.provider_publish_time)
      : null;

  return (
    <ButtonBase
      onClick={onClick}
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
        cursor: "pointer",
        textAlign: "left",
        width: "100%",
        transition: "background-color 0.15s ease, border-color 0.15s ease",
        "&:hover": {
          bgcolor: "rgba(255,255,255,0.05)",
          borderColor: "rgba(59,137,255,0.35)",
        },
      }}
    >
      {article.thumbnail_url ? (
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
      ) : (
        <Box
          component="img"
          src={NEWS_PLACEHOLDER_SVG}
          alt=""
          sx={{
            width: 72,
            height: 54,
            borderRadius: "6px",
            flexShrink: 0,
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
    </ButtonBase>
  );
}

// --- Article Detail Modal ---

interface ArticleModalProps {
  article: NewsArticle | null;
  open: boolean;
  onClose: () => void;
}

function ArticleModal({ article, open, onClose }: ArticleModalProps) {
  if (!article) return null;

  const absTime =
    article.provider_publish_time !== null
      ? formatAbsoluteTime(article.provider_publish_time)
      : null;
  const relTime =
    article.provider_publish_time !== null
      ? formatRelativeTime(article.provider_publish_time)
      : null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: "background.paper",
          borderRadius: "12px",
          maxHeight: "80vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "flex-start",
          gap: 1,
          pr: 6,
          pb: 1,
        }}
      >
        <Typography
          variant="h6"
          component="span"
          sx={{ fontWeight: 700, lineHeight: 1.35, fontSize: "1.05rem" }}
        >
          {article.title ?? "Untitled"}
        </Typography>
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8, color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 2 }}>
          {article.publisher && (
            <Chip
              label={article.publisher}
              size="small"
              sx={{
                bgcolor: "rgba(59,137,255,0.1)",
                color: "#3b89ff",
                fontWeight: 600,
                fontSize: "0.72rem",
                height: 22,
              }}
            />
          )}
          {article.type && (
            <Chip
              label={article.type}
              size="small"
              variant="outlined"
              sx={{ fontSize: "0.68rem", height: 22, textTransform: "capitalize" }}
            />
          )}
          {absTime && (
            <Typography
              variant="caption"
              sx={{ color: "text.disabled", fontFamily: "var(--font-geist-mono)", fontSize: "0.72rem" }}
            >
              {absTime} ({relTime})
            </Typography>
          )}
        </Box>

        {article.thumbnail_url ? (
          <Box
            component="img"
            src={article.thumbnail_url}
            alt={article.title ?? ""}
            sx={{
              width: "100%",
              maxHeight: 300,
              objectFit: "cover",
              borderRadius: "8px",
              mb: 2,
            }}
          />
        ) : (
          <Box
            component="img"
            src={NEWS_PLACEHOLDER_SVG}
            alt=""
            sx={{
              width: "100%",
              maxHeight: 160,
              objectFit: "contain",
              borderRadius: "8px",
              mb: 2,
              bgcolor: "rgba(255,255,255,0.03)",
            }}
          />
        )}

        {article.related_tickers && article.related_tickers.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography
              variant="caption"
              sx={{ color: "text.secondary", fontSize: "0.72rem", fontWeight: 600, mb: 0.5, display: "block" }}
            >
              Related Tickers
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {article.related_tickers.map((t) => (
                <Chip
                  key={t}
                  label={t}
                  size="small"
                  sx={{
                    bgcolor: "rgba(59,137,255,0.08)",
                    color: "#3b89ff",
                    borderRadius: "4px",
                    fontSize: "0.68rem",
                    fontFamily: "var(--font-geist-mono)",
                    fontWeight: 600,
                    height: 20,
                  }}
                />
              ))}
            </Box>
          </Box>
        )}

        {article.link && (
          <Button
            variant="outlined"
            size="small"
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            endIcon={<OpenInNewIcon sx={{ fontSize: "0.85rem !important" }} />}
            sx={{
              mt: 1,
              textTransform: "none",
              fontSize: "0.8rem",
              fontWeight: 600,
              borderRadius: "6px",
            }}
          >
            Read Full Article
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}

// --- Main component ---

export default function NewsFeed() {
  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [data, setData] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);

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

  const handleOpenArticle = useCallback((article: NewsArticle) => {
    setSelectedArticle(article);
  }, []);

  const handleCloseModal = useCallback(() => {
    setSelectedArticle(null);
  }, []);

  return (
    <>
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
                  key={article.uuid ?? article.link ?? article.title ?? ""}
                  article={article}
                  onClick={() => handleOpenArticle(article)}
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

      <ArticleModal
        article={selectedArticle}
        open={selectedArticle !== null}
        onClose={handleCloseModal}
      />
    </>
  );
}
