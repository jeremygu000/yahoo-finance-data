"use client";

import React, { useState, useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Switch from "@mui/material/Switch";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Tooltip from "@mui/material/Tooltip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import SendIcon from "@mui/icons-material/Send";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import WifiOffIcon from "@mui/icons-material/WifiOff";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { fetchAiHealth, fetchAiSummary, streamAiSummary, streamAiChat } from "@/lib/api";
import type { SummaryResponse, ChatMessage } from "@/lib/types";
import useTickers from "@/lib/useTickers";

const DAY_OPTIONS = [7, 14, 30, 60, 90];

const labelSx = {
  fontSize: "0.65rem",
  fontFamily: "var(--font-geist-mono)",
  color: "text.secondary",
  textTransform: "uppercase" as const,
  letterSpacing: "0.08em",
  fontWeight: 600,
  mb: 0.5,
};

const cardSx = {
  bgcolor: "background.paper",
  border: "1px solid",
  borderColor: "divider",
  borderRadius: "12px",
  p: 2.5,
};

function parseThinkTags(text: string): {
  thinkingText: string;
  responseText: string;
  thinkingDone: boolean;
} {
  const openIdx = text.indexOf("<think>");
  if (openIdx === -1) {
    return { thinkingText: "", responseText: text, thinkingDone: false };
  }

  const closeIdx = text.indexOf("</think>");
  if (closeIdx === -1) {
    const thinkingText = text.slice(openIdx + "<think>".length);
    return { thinkingText, responseText: "", thinkingDone: false };
  }

  const thinkingText = text.slice(openIdx + "<think>".length, closeIdx);
  const responseText = text.slice(closeIdx + "</think>".length);
  return { thinkingText, responseText, thinkingDone: true };
}

export default function AISummary() {
  const { tickers, loading: tickersLoading } = useTickers();

  const [available, setAvailable] = useState<boolean | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [days, setDays] = useState(30);
  const [streaming, setStreaming] = useState(true);

  const [generating, setGenerating] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [thinkingExpanded, setThinkingExpanded] = useState(false);

  const abortRef = useRef(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const chatMsgIdRef = useRef(0);
  const nextChatMsgId = () => `chat-${++chatMsgIdRef.current}`;
  const [chatInput, setChatInput] = useState("");
  const [chatStreaming, setChatStreaming] = useState(false);
  const [chatStreamedText, setChatStreamedText] = useState("");
  const chatStreamedRef = useRef("");

  useEffect(() => {
    let cancelled = false;
    setHealthLoading(true);
    fetchAiHealth()
      .then((data) => {
        if (!cancelled) setAvailable(data.available);
      })
      .catch(() => {
        if (!cancelled) setAvailable(false);
      })
      .finally(() => {
        if (!cancelled) setHealthLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (tickers.length > 0 && selectedTickers.length === 0) {
      setSelectedTickers(tickers.slice(0, 5));
    }
  }, [tickers, selectedTickers.length]);

  const displayText = streaming ? streamedText : result?.summary ?? "";
  const { thinkingText, responseText, thinkingDone } = parseThinkTags(displayText);
  const hasThinking = thinkingText.length > 0;

  useEffect(() => {
    if (hasThinking && !thinkingDone) {
      setThinkingExpanded(true);
    }
  }, [hasThinking, thinkingDone]);

  useEffect(() => {
    if (thinkingDone) {
      setThinkingExpanded(false);
    }
  }, [thinkingDone]);

  const toggleTicker = (ticker: string) => {
    setSelectedTickers((prev) =>
      prev.includes(ticker) ? prev.filter((t) => t !== ticker) : [...prev, ticker],
    );
  };

  const selectAll = () => setSelectedTickers([...tickers]);
  const deselectAll = () => setSelectedTickers([]);

  const handleGenerate = async () => {
    setError(null);
    setResult(null);
    setStreamedText("");
    setThinkingExpanded(false);
    setGenerating(true);
    abortRef.current = false;
    setChatMessages([]);
    chatMsgIdRef.current = 0;
    setChatSessionId(null);
    setChatStreamedText("");

    const req = {
      tickers: selectedTickers.length > 0 ? selectedTickers : undefined,
      days,
    };

    try {
      if (streaming) {
        await streamAiSummary(
          req,
          (token) => {
            if (!abortRef.current) setStreamedText((prev) => prev + token);
          },
          () => {
            if (!abortRef.current) setGenerating(false);
          },
        );
      } else {
        const data = await fetchAiSummary(req);
        if (!abortRef.current) {
          setResult(data);
          setGenerating(false);
        }
      }
    } catch (err) {
      if (!abortRef.current) {
        setError(err instanceof Error ? err.message : "Failed to generate summary");
        setGenerating(false);
      }
    }
  };

  const hasOutput = displayText.length > 0;

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatStreamedText]);

  const handleSendChat = async () => {
    const message = chatInput.trim();
    if (!message || chatStreaming || generating) return;

    setChatMessages((prev) => [...prev, { id: nextChatMsgId(), role: "user", content: message }]);
    setChatInput("");
    setChatStreaming(true);
    setChatStreamedText("");
    chatStreamedRef.current = "";

    try {
      await streamAiChat(
        { message, session_id: chatSessionId ?? undefined, tickers: selectedTickers, days },
        (sessionId) => { setChatSessionId(sessionId); },
        (token) => {
          chatStreamedRef.current += token;
          setChatStreamedText((prev) => prev + token);
        },
        () => {
          const finalText = chatStreamedRef.current;
          setChatMessages((prev) => [...prev, { id: nextChatMsgId(), role: "assistant" as const, content: finalText }]);
          setChatStreamedText("");
          chatStreamedRef.current = "";
          setChatStreaming(false);
        },
      );
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { id: nextChatMsgId(), role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}` },
      ]);
      setChatStreamedText("");
      chatStreamedRef.current = "";
      setChatStreaming(false);
    }
  };

  const metaData = result
    ? { model: result.model, evalCount: result.eval_count, durationMs: result.total_duration_ms }
    : null;

  const isStreamingThinking = generating && streaming && hasThinking && !thinkingDone;
  const isStreamingResponse = generating && streaming && (!hasThinking || thinkingDone);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={cardSx}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5, flexWrap: "wrap", gap: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <AutoAwesomeIcon sx={{ color: "#3b89ff", fontSize: "1.3rem" }} />
            <Typography
              sx={{
                fontFamily: "var(--font-geist-sans)",
                fontWeight: 700,
                fontSize: "0.95rem",
                color: "text.primary",
              }}
            >
              AI Market Analysis
            </Typography>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {healthLoading ? (
              <CircularProgress size={12} sx={{ color: "text.disabled" }} />
            ) : available ? (
              <>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: "#36bb80",
                    "@keyframes aiPulse": {
                      "0%, 100%": { opacity: 1, transform: "scale(1)" },
                      "50%": { opacity: 0.6, transform: "scale(0.8)" },
                    },
                    animation: "aiPulse 2.5s ease-in-out infinite",
                  }}
                />
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "#36bb80" }}>
                  Ollama Online
                </Typography>
              </>
            ) : (
              <>
                <WifiOffIcon sx={{ fontSize: "0.9rem", color: "#ff7134" }} />
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "#ff7134" }}>
                  Ollama Offline
                </Typography>
              </>
            )}
          </Box>
        </Box>

        <Box sx={{ mb: 2.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
            <Typography sx={labelSx}>Tickers</Typography>
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button
                size="small"
                onClick={selectAll}
                disabled={tickersLoading}
                sx={{
                  fontSize: "0.65rem",
                  fontFamily: "var(--font-geist-mono)",
                  color: "text.secondary",
                  minWidth: 0,
                  px: 1,
                  py: 0.25,
                  textTransform: "none",
                  "&:hover": { color: "#3b89ff" },
                }}
              >
                Select All
              </Button>
              <Button
                size="small"
                onClick={deselectAll}
                disabled={tickersLoading}
                sx={{
                  fontSize: "0.65rem",
                  fontFamily: "var(--font-geist-mono)",
                  color: "text.secondary",
                  minWidth: 0,
                  px: 1,
                  py: 0.25,
                  textTransform: "none",
                  "&:hover": { color: "#ff7134" },
                }}
              >
                Deselect All
              </Button>
            </Box>
          </Box>
          {tickersLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={14} sx={{ color: "text.disabled" }} />
              <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.disabled" }}>
                Loading tickers...
              </Typography>
            </Box>
          ) : (
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap: 0.5,
                maxHeight: 120,
                overflowY: "auto",
                "&::-webkit-scrollbar": { width: 4 },
                "&::-webkit-scrollbar-track": { bgcolor: "transparent" },
                "&::-webkit-scrollbar-thumb": { bgcolor: "rgba(255,255,255,0.08)", borderRadius: 2 },
              }}
            >
              {tickers.map((ticker) => {
                const checked = selectedTickers.includes(ticker);
                return (
                  <Tooltip key={ticker} title={ticker} placement="top">
                    <FormControlLabel
                      control={
                        <Checkbox
                          size="small"
                          checked={checked}
                          onChange={() => toggleTicker(ticker)}
                          sx={{
                            p: 0.25,
                            color: "text.disabled",
                            "&.Mui-checked": { color: "#3b89ff" },
                          }}
                        />
                      }
                      label={
                        <Typography
                          sx={{
                            fontFamily: "var(--font-geist-mono)",
                            fontSize: "0.75rem",
                            fontWeight: checked ? 600 : 400,
                            color: checked ? "#3b89ff" : "text.secondary",
                            transition: "color 0.15s ease",
                          }}
                        >
                          {ticker}
                        </Typography>
                      }
                      sx={{ m: 0, mr: 0.5 }}
                    />
                  </Tooltip>
                );
              })}
            </Box>
          )}
          {selectedTickers.length > 0 && (
            <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.65rem", color: "text.disabled", mt: 0.75 }}>
              {selectedTickers.length} ticker{selectedTickers.length !== 1 ? "s" : ""} selected
            </Typography>
          )}
        </Box>

        <Box sx={{ mb: 2.5 }}>
          <Typography sx={labelSx}>Time Range</Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {DAY_OPTIONS.map((d) => (
              <Chip
                key={d}
                label={`${d}d`}
                size="small"
                onClick={() => setDays(d)}
                sx={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  height: 24,
                  cursor: "pointer",
                  bgcolor: days === d ? "rgba(59,137,255,0.18)" : "transparent",
                  color: days === d ? "#3b89ff" : "text.secondary",
                  border: "1px solid",
                  borderColor: days === d ? "rgba(59,137,255,0.4)" : "divider",
                  transition: "all 0.15s ease",
                  "&:hover": {
                    bgcolor: "rgba(59,137,255,0.1)",
                    color: "#3b89ff",
                    borderColor: "rgba(59,137,255,0.3)",
                  },
                }}
              />
            ))}
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
          <Button
            variant="contained"
            startIcon={
              generating ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <PlayArrowIcon />
              )
            }
            onClick={handleGenerate}
            disabled={generating || available === false || selectedTickers.length === 0}
            sx={{
              bgcolor: "#3b89ff",
              "&:hover": { bgcolor: "#2a78ee" },
              "&.Mui-disabled": { bgcolor: "rgba(59,137,255,0.25)", color: "rgba(255,255,255,0.35)" },
              borderRadius: "8px",
              fontFamily: "var(--font-geist-sans)",
              fontWeight: 600,
              fontSize: "0.875rem",
              px: 2.5,
              textTransform: "none",
            }}
          >
            {generating ? "Generating..." : "Generate Summary"}
          </Button>

          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={streaming}
                onChange={(e) => setStreaming(e.target.checked)}
                sx={{
                  "& .MuiSwitch-switchBase.Mui-checked": { color: "#3b89ff" },
                  "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": { bgcolor: "#3b89ff" },
                }}
              />
            }
            label={
              <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                Streaming
              </Typography>
            }
          />
        </Box>
      </Box>

      {error && (
        <Box
          sx={{
            bgcolor: "rgba(255,113,52,0.08)",
            border: "1px solid rgba(255,113,52,0.3)",
            borderRadius: "10px",
            px: 2.5,
            py: 2,
          }}
        >
          <Typography
            sx={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.825rem",
              color: "#ff7134",
            }}
          >
            {error}
          </Typography>
        </Box>
      )}

      {generating && !hasOutput && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            px: 2.5,
            py: 3,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "12px",
          }}
        >
          <CircularProgress size={20} sx={{ color: "#3b89ff", flexShrink: 0 }} />
          <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.825rem", color: "text.secondary" }}>
            Generating analysis...
          </Typography>
        </Box>
      )}

      {hasOutput && (
        <Paper
          elevation={0}
          sx={{
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "12px",
            overflow: "hidden",
            "@keyframes fadeInResult": {
              from: { opacity: 0, transform: "translateY(6px)" },
              to: { opacity: 1, transform: "translateY(0)" },
            },
            animation: "fadeInResult 0.25s ease-out",
          }}
        >
          <Box
            sx={{
              px: 2.5,
              py: 1.5,
              borderBottom: "1px solid",
              borderColor: "divider",
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <AutoAwesomeIcon sx={{ fontSize: "0.9rem", color: "#3b89ff" }} />
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: "0.7rem",
                color: "text.secondary",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                fontWeight: 600,
              }}
            >
              Analysis Output
            </Typography>
            {generating && (
              <Box
                sx={{
                  ml: "auto",
                  display: "flex",
                  alignItems: "center",
                  gap: 0.75,
                }}
              >
                <CircularProgress size={10} sx={{ color: "#3b89ff" }} />
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.65rem", color: "#3b89ff" }}>
                  streaming
                </Typography>
              </Box>
            )}
          </Box>

          {hasThinking && (
            <Box
              sx={{
                borderBottom: responseText.length > 0 ? "1px solid" : "none",
                borderColor: "divider",
                bgcolor: "rgba(156,124,255,0.04)",
                borderLeft: "3px solid #9c7cff",
              }}
            >
              <Box
                onClick={() => setThinkingExpanded((prev) => !prev)}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  px: 2,
                  py: 1,
                  cursor: "pointer",
                  userSelect: "none",
                  "&:hover": { bgcolor: "rgba(156,124,255,0.06)" },
                  transition: "background-color 0.15s ease",
                }}
              >
                <Typography
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    fontSize: "0.7rem",
                    color: "#9c7cff",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    flexGrow: 1,
                  }}
                >
                  {thinkingDone ? "🧠 Thinking" : "🧠 Thinking..."}
                </Typography>
                <IconButton
                  size="small"
                  tabIndex={-1}
                  sx={{
                    p: 0.25,
                    color: "#9c7cff",
                    transition: "transform 0.2s ease",
                    transform: thinkingExpanded ? "rotate(0deg)" : "rotate(-90deg)",
                    pointerEvents: "none",
                  }}
                >
                  <ExpandMoreIcon sx={{ fontSize: "1rem" }} />
                </IconButton>
              </Box>

              <Collapse in={thinkingExpanded} timeout={200}>
                <Box sx={{ px: 2.5, pb: 2, pt: 0.5 }}>
                  <Typography
                    component="pre"
                    sx={{
                      fontFamily: "var(--font-geist-mono)",
                      fontSize: "0.775rem",
                      lineHeight: 1.7,
                      color: "rgba(156,124,255,0.75)",
                      fontStyle: "italic",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      m: 0,
                    }}
                  >
                    {thinkingText}
                    {isStreamingThinking && (
                      <Box
                        component="span"
                        sx={{
                          display: "inline-block",
                          width: "0.5em",
                          height: "1em",
                          bgcolor: "#9c7cff",
                          ml: "1px",
                          verticalAlign: "text-bottom",
                          "@keyframes blink": {
                            "0%, 100%": { opacity: 1 },
                            "50%": { opacity: 0 },
                          },
                          animation: "blink 0.9s step-end infinite",
                        }}
                      />
                    )}
                  </Typography>
                </Box>
              </Collapse>
            </Box>
          )}

          {(responseText.length > 0 || (!hasThinking && hasOutput)) && (
            <Box sx={{ px: 2.5, py: 2.5 }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => (
                    <Typography
                      variant="h5"
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontWeight: 700,
                        fontSize: "1.15rem",
                        mb: 1,
                        mt: 1.5,
                        color: "text.primary",
                      }}
                    >
                      {children}
                    </Typography>
                  ),
                  h2: ({ children }) => (
                    <Typography
                      variant="h6"
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontWeight: 600,
                        fontSize: "1rem",
                        mb: 0.75,
                        mt: 1.5,
                        color: "text.primary",
                      }}
                    >
                      {children}
                    </Typography>
                  ),
                  h3: ({ children }) => (
                    <Typography
                      variant="subtitle1"
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontWeight: 600,
                        fontSize: "0.9rem",
                        mb: 0.5,
                        mt: 1.25,
                        color: "text.primary",
                      }}
                    >
                      {children}
                    </Typography>
                  ),
                  p: ({ children }) => (
                    <Typography
                      component="p"
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontSize: "0.825rem",
                        lineHeight: 1.75,
                        color: "text.primary",
                        mb: 1,
                        mt: 0,
                      }}
                    >
                      {children}
                    </Typography>
                  ),
                  strong: ({ children }) => (
                    <Box component="span" sx={{ fontWeight: 700 }}>
                      {children}
                    </Box>
                  ),
                  em: ({ children }) => (
                    <Box component="span" sx={{ fontStyle: "italic" }}>
                      {children}
                    </Box>
                  ),
                  ul: ({ children }) => (
                    <Box
                      component="ul"
                      sx={{
                        pl: 2.5,
                        mb: 1,
                        mt: 0,
                        "& li": { mb: 0.25 },
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  ol: ({ children }) => (
                    <Box
                      component="ol"
                      sx={{
                        pl: 2.5,
                        mb: 1,
                        mt: 0,
                        "& li": { mb: 0.25 },
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  li: ({ children }) => (
                    <Box
                      component="li"
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontSize: "0.825rem",
                        lineHeight: 1.75,
                        color: "text.primary",
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  code: ({ inline, children, ...props }: { inline?: boolean; children?: React.ReactNode; className?: string }) =>
                    inline ? (
                      <Box
                        component="code"
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.78rem",
                          bgcolor: "rgba(59,137,255,0.1)",
                          color: "#3b89ff",
                          px: 0.6,
                          py: 0.15,
                          borderRadius: "4px",
                        }}
                        {...props}
                      >
                        {children}
                      </Box>
                    ) : (
                      <Box
                        component="code"
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.78rem",
                          display: "block",
                        }}
                        {...props}
                      >
                        {children}
                      </Box>
                    ),
                  pre: ({ children }) => (
                    <Box
                      component="pre"
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontSize: "0.78rem",
                        bgcolor: "rgba(0,0,0,0.35)",
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: "8px",
                        p: 1.5,
                        mb: 1.5,
                        mt: 0.5,
                        overflowX: "auto",
                        whiteSpace: "pre",
                        lineHeight: 1.6,
                        color: "text.primary",
                        m: 0,
                        "& code": {
                          bgcolor: "transparent",
                          p: 0,
                          borderRadius: 0,
                          color: "inherit",
                          fontSize: "inherit",
                        },
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  a: ({ href, children }) => (
                    <Box
                      component="a"
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        color: "#3b89ff",
                        textDecoration: "none",
                        "&:hover": { textDecoration: "underline" },
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  table: ({ children }) => (
                    <Box
                      component="table"
                      sx={{
                        width: "100%",
                        borderCollapse: "collapse",
                        mb: 1.5,
                        fontSize: "0.8rem",
                        fontFamily: "var(--font-geist-sans)",
                        "& th, & td": {
                          border: "1px solid",
                          borderColor: "divider",
                          px: 1.5,
                          py: 0.75,
                          textAlign: "left",
                        },
                        "& th": {
                          fontWeight: 600,
                          bgcolor: "rgba(59,137,255,0.07)",
                          color: "text.secondary",
                        },
                        "& tr:nth-of-type(even) td": {
                          bgcolor: "rgba(255,255,255,0.02)",
                        },
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  blockquote: ({ children }) => (
                    <Box
                      component="blockquote"
                      sx={{
                        borderLeft: "3px solid #3b89ff",
                        pl: 1.5,
                        ml: 0,
                        mb: 1,
                        color: "text.secondary",
                        fontStyle: "italic",
                        fontFamily: "var(--font-geist-sans)",
                        fontSize: "0.825rem",
                      }}
                    >
                      {children}
                    </Box>
                  ),
                  hr: () => (
                    <Box
                      component="hr"
                      sx={{
                        border: "none",
                        borderTop: "1px solid",
                        borderColor: "divider",
                        my: 1.5,
                      }}
                    />
                  ),
                }}
              >
                {hasThinking ? responseText : displayText}
              </ReactMarkdown>
              {isStreamingResponse && (
                <Box
                  component="span"
                  sx={{
                    display: "inline-block",
                    width: "0.5em",
                    height: "1em",
                    bgcolor: "#3b89ff",
                    ml: "1px",
                    verticalAlign: "text-bottom",
                    "@keyframes blink": {
                      "0%, 100%": { opacity: 1 },
                      "50%": { opacity: 0 },
                    },
                    animation: "blink 0.9s step-end infinite",
                  }}
                />
              )}
            </Box>
          )}

          {metaData && (
            <Box
              sx={{
                px: 2.5,
                py: 1.5,
                borderTop: "1px solid",
                borderColor: "divider",
                display: "flex",
                gap: 3,
                flexWrap: "wrap",
              }}
            >
              <Box>
                <Typography sx={labelSx}>Model</Typography>
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                  {metaData.model}
                </Typography>
              </Box>
              <Box>
                <Typography sx={labelSx}>Tokens</Typography>
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                  {metaData.evalCount.toLocaleString()}
                </Typography>
              </Box>
              <Box>
                <Typography sx={labelSx}>Duration</Typography>
                <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>
                  {(metaData.durationMs / 1000).toFixed(1)}s
                </Typography>
              </Box>
            </Box>
          )}
        </Paper>
      )}

      {hasOutput && chatMessages.length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {chatMessages.map((msg) => {
            if (msg.role === "user") {
              return (
                <Box
                  key={msg.id}
                  sx={{
                    display: "flex",
                    justifyContent: "flex-end",
                  }}
                >
                  <Box
                    sx={{
                      maxWidth: "80%",
                      bgcolor: "rgba(59,137,255,0.12)",
                      borderRight: "3px solid #3b89ff",
                      borderRadius: "12px 4px 12px 12px",
                      px: 2,
                      py: 1.25,
                    }}
                  >
                    <Typography
                      sx={{
                        fontFamily: "var(--font-geist-sans)",
                        fontSize: "0.825rem",
                        lineHeight: 1.65,
                        color: "text.primary",
                      }}
                    >
                      {msg.content}
                    </Typography>
                  </Box>
                </Box>
              );
            }
            const { thinkingText: msgThinking, responseText: msgResponse, thinkingDone: msgThinkingDone } = parseThinkTags(msg.content);
            const msgHasThinking = msgThinking.length > 0;
            return (
              <Paper
                key={msg.id}
                elevation={0}
                sx={{
                  bgcolor: "background.paper",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: "4px 12px 12px 12px",
                  overflow: "hidden",
                }}
              >
                {msgHasThinking && (
                  <Box
                    sx={{
                      borderBottom: msgResponse.length > 0 ? "1px solid" : "none",
                      borderColor: "divider",
                      bgcolor: "rgba(156,124,255,0.04)",
                      borderLeft: "3px solid #9c7cff",
                    }}
                  >
                    <Box sx={{ px: 2, py: 1 }}>
                      <Typography
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.7rem",
                          color: "#9c7cff",
                          fontWeight: 600,
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                        }}
                      >
                        {msgThinkingDone ? "🧠 Thinking" : "🧠 Thinking..."}
                      </Typography>
                    </Box>
                    <Box sx={{ px: 2.5, pb: 2, pt: 0 }}>
                      <Typography
                        component="pre"
                        sx={{
                          fontFamily: "var(--font-geist-mono)",
                          fontSize: "0.775rem",
                          lineHeight: 1.7,
                          color: "rgba(156,124,255,0.75)",
                          fontStyle: "italic",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          m: 0,
                        }}
                      >
                        {msgThinking}
                      </Typography>
                    </Box>
                  </Box>
                )}
                <Box sx={{ px: 2.5, py: 2 }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => (
                        <Typography variant="h5" sx={{ fontFamily: "var(--font-geist-sans)", fontWeight: 700, fontSize: "1.15rem", mb: 1, mt: 1.5, color: "text.primary" }}>{children}</Typography>
                      ),
                      h2: ({ children }) => (
                        <Typography variant="h6" sx={{ fontFamily: "var(--font-geist-sans)", fontWeight: 600, fontSize: "1rem", mb: 0.75, mt: 1.5, color: "text.primary" }}>{children}</Typography>
                      ),
                      h3: ({ children }) => (
                        <Typography variant="subtitle1" sx={{ fontFamily: "var(--font-geist-sans)", fontWeight: 600, fontSize: "0.9rem", mb: 0.5, mt: 1.25, color: "text.primary" }}>{children}</Typography>
                      ),
                      p: ({ children }) => (
                        <Typography component="p" sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.825rem", lineHeight: 1.75, color: "text.primary", mb: 1, mt: 0 }}>{children}</Typography>
                      ),
                      strong: ({ children }) => <Box component="span" sx={{ fontWeight: 700 }}>{children}</Box>,
                      em: ({ children }) => <Box component="span" sx={{ fontStyle: "italic" }}>{children}</Box>,
                      ul: ({ children }) => <Box component="ul" sx={{ pl: 2.5, mb: 1, mt: 0, "& li": { mb: 0.25 } }}>{children}</Box>,
                      ol: ({ children }) => <Box component="ol" sx={{ pl: 2.5, mb: 1, mt: 0, "& li": { mb: 0.25 } }}>{children}</Box>,
                      li: ({ children }) => <Box component="li" sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.825rem", lineHeight: 1.75, color: "text.primary" }}>{children}</Box>,
                      code: ({ inline, children, ...props }: { inline?: boolean; children?: React.ReactNode; className?: string }) =>
                        inline ? (
                          <Box component="code" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", bgcolor: "rgba(59,137,255,0.1)", color: "#3b89ff", px: 0.6, py: 0.15, borderRadius: "4px" }} {...props}>{children}</Box>
                        ) : (
                          <Box component="code" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", display: "block" }} {...props}>{children}</Box>
                        ),
                      pre: ({ children }) => (
                        <Box component="pre" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", bgcolor: "rgba(0,0,0,0.35)", border: "1px solid", borderColor: "divider", borderRadius: "8px", p: 1.5, mb: 1.5, mt: 0.5, overflowX: "auto", whiteSpace: "pre", lineHeight: 1.6, color: "text.primary", m: 0, "& code": { bgcolor: "transparent", p: 0, borderRadius: 0, color: "inherit", fontSize: "inherit" } }}>{children}</Box>
                      ),
                      a: ({ href, children }) => <Box component="a" href={href} target="_blank" rel="noopener noreferrer" sx={{ color: "#3b89ff", textDecoration: "none", "&:hover": { textDecoration: "underline" } }}>{children}</Box>,
                      table: ({ children }) => (
                        <Box component="table" sx={{ width: "100%", borderCollapse: "collapse", mb: 1.5, fontSize: "0.8rem", fontFamily: "var(--font-geist-sans)", "& th, & td": { border: "1px solid", borderColor: "divider", px: 1.5, py: 0.75, textAlign: "left" }, "& th": { fontWeight: 600, bgcolor: "rgba(59,137,255,0.07)", color: "text.secondary" }, "& tr:nth-of-type(even) td": { bgcolor: "rgba(255,255,255,0.02)" } }}>{children}</Box>
                      ),
                      blockquote: ({ children }) => <Box component="blockquote" sx={{ borderLeft: "3px solid #3b89ff", pl: 1.5, ml: 0, mb: 1, color: "text.secondary", fontStyle: "italic", fontFamily: "var(--font-geist-sans)", fontSize: "0.825rem" }}>{children}</Box>,
                      hr: () => <Box component="hr" sx={{ border: "none", borderTop: "1px solid", borderColor: "divider", my: 1.5 }} />,
                    }}
                  >
                    {msgHasThinking ? msgResponse : msg.content}
                  </ReactMarkdown>
                </Box>
              </Paper>
            );
          })}

          {chatStreaming && (
            <Paper
              elevation={0}
              sx={{
                bgcolor: "background.paper",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "4px 12px 12px 12px",
                overflow: "hidden",
              }}
            >
              {(() => {
                const { thinkingText: st, responseText: sr, thinkingDone: sd } = parseThinkTags(chatStreamedText);
                const sHasThinking = st.length > 0;
                const sIsThinking = sHasThinking && !sd;
                const sIsResponding = !sHasThinking || sd;
                return (
                  <>
                    {sHasThinking && (
                      <Box sx={{ borderBottom: sr.length > 0 ? "1px solid" : "none", borderColor: "divider", bgcolor: "rgba(156,124,255,0.04)", borderLeft: "3px solid #9c7cff" }}>
                        <Box sx={{ px: 2, py: 1 }}>
                          <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "#9c7cff", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                            {sd ? "🧠 Thinking" : "🧠 Thinking..."}
                          </Typography>
                        </Box>
                        <Box sx={{ px: 2.5, pb: 2, pt: 0 }}>
                          <Typography component="pre" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.775rem", lineHeight: 1.7, color: "rgba(156,124,255,0.75)", fontStyle: "italic", whiteSpace: "pre-wrap", wordBreak: "break-word", m: 0 }}>
                            {st}
                            {sIsThinking && (
                              <Box component="span" sx={{ display: "inline-block", width: "0.5em", height: "1em", bgcolor: "#9c7cff", ml: "1px", verticalAlign: "text-bottom", "@keyframes blink": { "0%, 100%": { opacity: 1 }, "50%": { opacity: 0 } }, animation: "blink 0.9s step-end infinite" }} />
                            )}
                          </Typography>
                        </Box>
                      </Box>
                    )}
                    {(sr.length > 0 || (!sHasThinking && chatStreamedText.length > 0)) && (
                      <Box sx={{ px: 2.5, py: 2 }}>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <Typography component="p" sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.825rem", lineHeight: 1.75, color: "text.primary", mb: 1, mt: 0 }}>{children}</Typography>,
                            strong: ({ children }) => <Box component="span" sx={{ fontWeight: 700 }}>{children}</Box>,
                            em: ({ children }) => <Box component="span" sx={{ fontStyle: "italic" }}>{children}</Box>,
                            ul: ({ children }) => <Box component="ul" sx={{ pl: 2.5, mb: 1, mt: 0, "& li": { mb: 0.25 } }}>{children}</Box>,
                            ol: ({ children }) => <Box component="ol" sx={{ pl: 2.5, mb: 1, mt: 0, "& li": { mb: 0.25 } }}>{children}</Box>,
                            li: ({ children }) => <Box component="li" sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.825rem", lineHeight: 1.75, color: "text.primary" }}>{children}</Box>,
                            code: ({ inline, children, ...props }: { inline?: boolean; children?: React.ReactNode; className?: string }) =>
                              inline ? <Box component="code" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", bgcolor: "rgba(59,137,255,0.1)", color: "#3b89ff", px: 0.6, py: 0.15, borderRadius: "4px" }} {...props}>{children}</Box>
                                     : <Box component="code" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", display: "block" }} {...props}>{children}</Box>,
                            pre: ({ children }) => <Box component="pre" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.78rem", bgcolor: "rgba(0,0,0,0.35)", border: "1px solid", borderColor: "divider", borderRadius: "8px", p: 1.5, mb: 1.5, mt: 0.5, overflowX: "auto", whiteSpace: "pre", lineHeight: 1.6, color: "text.primary", m: 0, "& code": { bgcolor: "transparent", p: 0, borderRadius: 0, color: "inherit", fontSize: "inherit" } }}>{children}</Box>,
                            a: ({ href, children }) => <Box component="a" href={href} target="_blank" rel="noopener noreferrer" sx={{ color: "#3b89ff", textDecoration: "none", "&:hover": { textDecoration: "underline" } }}>{children}</Box>,
                          }}
                        >
                          {sHasThinking ? sr : chatStreamedText}
                        </ReactMarkdown>
                        {sIsResponding && (
                          <Box component="span" sx={{ display: "inline-block", width: "0.5em", height: "1em", bgcolor: "#3b89ff", ml: "1px", verticalAlign: "text-bottom", "@keyframes blink": { "0%, 100%": { opacity: 1 }, "50%": { opacity: 0 } }, animation: "blink 0.9s step-end infinite" }} />
                        )}
                      </Box>
                    )}
                    {!sHasThinking && chatStreamedText.length === 0 && (
                      <Box sx={{ px: 2.5, py: 2, display: "flex", alignItems: "center", gap: 1 }}>
                        <CircularProgress size={12} sx={{ color: "#3b89ff" }} />
                        <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.75rem", color: "text.secondary" }}>Thinking...</Typography>
                      </Box>
                    )}
                  </>
                );
              })()}
            </Paper>
          )}

          <div ref={chatBottomRef} />
        </Box>
      )}

      {hasOutput && (
        <Box
          sx={{
            display: "flex",
            gap: 1,
            alignItems: "flex-end",
            p: 1.5,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "12px",
          }}
        >
          <TextField
            fullWidth
            multiline
            minRows={1}
            maxRows={3}
            placeholder="Ask a follow-up question about this analysis..."
            value={chatInput}
            onChange={(e) => { setChatInput(e.target.value); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSendChat();
              }
            }}
            disabled={chatStreaming || generating}
            variant="outlined"
            size="small"
            sx={{
              "& .MuiOutlinedInput-root": {
                fontFamily: "var(--font-geist-sans)",
                fontSize: "0.825rem",
                borderRadius: "8px",
                "& fieldset": { borderColor: "divider" },
                "&:hover fieldset": { borderColor: "rgba(59,137,255,0.4)" },
                "&.Mui-focused fieldset": { borderColor: "#3b89ff" },
              },
              "& .MuiInputBase-input::placeholder": {
                color: "text.disabled",
                opacity: 1,
              },
            }}
          />
          <IconButton
            onClick={() => { void handleSendChat(); }}
            disabled={chatStreaming || generating || chatInput.trim().length === 0}
            sx={{
              bgcolor: "#3b89ff",
              color: "#fff",
              borderRadius: "8px",
              width: 36,
              height: 36,
              flexShrink: 0,
              "&:hover": { bgcolor: "#2a78ee" },
              "&.Mui-disabled": { bgcolor: "rgba(59,137,255,0.2)", color: "rgba(255,255,255,0.3)" },
            }}
          >
            {chatStreaming ? <CircularProgress size={14} color="inherit" /> : <SendIcon sx={{ fontSize: "1rem" }} />}
          </IconButton>
        </Box>
      )}

      {!hasOutput && !generating && !error && (
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
          <AutoAwesomeIcon sx={{ fontSize: "2rem", color: "text.disabled" }} />
          <Typography sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.8rem", color: "text.disabled" }}>
            No analysis yet
          </Typography>
          <Typography sx={{ fontFamily: "var(--font-geist-sans)", fontSize: "0.75rem", color: "text.disabled" }}>
            Select tickers and click Generate Summary to get your first AI market analysis
          </Typography>
        </Box>
      )}
    </Box>
  );
}
