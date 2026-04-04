"use client";

import { useEffect, useRef, useState } from "react";
import { Command } from "cmdk";
import Dialog from "@mui/material/Dialog";
import Box from "@mui/material/Box";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import CandlestickChartIcon from "@mui/icons-material/CandlestickChart";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import TableChartIcon from "@mui/icons-material/TableChart";
import SpeedIcon from "@mui/icons-material/Speed";
import TimelineIcon from "@mui/icons-material/Timeline";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import NotificationsIcon from "@mui/icons-material/Notifications";
import SearchIcon from "@mui/icons-material/Search";

import { searchTickers } from "@/lib/api";
import { useThemeMode } from "@/components/ThemeProvider";
import type { SearchResult } from "@/lib/types";

const dotSx = (hasData: boolean) => ({
  width: 7,
  height: 7,
  borderRadius: "50%",
  bgcolor: hasData ? "#36bb80" : "rgba(255,255,255,0.2)",
  flexShrink: 0,
});

const SECTIONS = [
  { id: "overview", label: "Overview", icon: ShowChartIcon },
  { id: "candlestick", label: "Candlestick", icon: CandlestickChartIcon },
  { id: "comparison", label: "Comparison", icon: CompareArrowsIcon },
  { id: "table", label: "Data Table", icon: TableChartIcon },
  { id: "vix", label: "VIX", icon: SpeedIcon },
  { id: "indicators", label: "Indicators", icon: TimelineIcon },
  { id: "alerts", label: "Alerts", icon: NotificationsIcon },
];

export default function CommandPalette() {
  const [open, setOpen] = useState<boolean>(false);
  const [query, setQuery] = useState<string>("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { mode, toggleMode } = useThemeMode();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleClose = () => {
    setOpen(false);
    setQuery("");
    setResults([]);
    setLoading(false);
    if (debounceRef.current) clearTimeout(debounceRef.current);
  };

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchTickers(query);
        setResults(res.results);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    handleClose();
  };

  const navigatePortfolio = () => {
    handleClose();
    window.location.href = "/portfolio";
  };

  const handleToggleTheme = () => {
    toggleMode();
    handleClose();
  };

  const containerSx = {
    bgcolor: "#0f1729",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "12px",
    overflow: "hidden",
    width: "100%",
    maxWidth: 560,
    mx: "auto",
    boxShadow: "0 24px 64px rgba(0,0,0,0.6), 0 4px 16px rgba(0,0,0,0.4)",
    animation: "cmdFadeIn 0.15s ease-out",
    "@keyframes cmdFadeIn": {
      from: { opacity: 0, transform: "translateY(-8px) scale(0.98)" },
      to: { opacity: 1, transform: "translateY(0) scale(1)" },
    },
  };

  const inputWrapperSx = {
    display: "flex",
    alignItems: "center",
    gap: 1,
    px: 2,
    py: 1.5,
    borderBottom: "1px solid rgba(255,255,255,0.08)",
  };

  const badgeSx = {
    display: "flex",
    alignItems: "center",
    gap: 0.5,
    px: 0.75,
    py: 0.25,
    bgcolor: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "6px",
    fontFamily: "var(--font-geist-mono)",
    fontSize: "0.65rem",
    color: "rgba(255,255,255,0.35)",
    letterSpacing: "0.04em",
    userSelect: "none",
    whiteSpace: "nowrap",
  };

  const listSx = {
    maxHeight: 360,
    overflowY: "auto" as const,
    py: 1,
    "&::-webkit-scrollbar": { width: 4 },
    "&::-webkit-scrollbar-track": { bgcolor: "transparent" },
    "&::-webkit-scrollbar-thumb": {
      bgcolor: "rgba(255,255,255,0.08)",
      borderRadius: 2,
    },
  };

  const groupLabelSx = {
    display: "block",
    px: 2,
    pt: 1.5,
    pb: 0.5,
    fontSize: "0.65rem",
    color: "rgba(255,255,255,0.35)",
    fontFamily: "var(--font-geist-mono)",
    textTransform: "uppercase" as const,
    letterSpacing: "0.08em",
    fontWeight: 600,
  };

  const itemSx = {
    display: "flex",
    alignItems: "center",
    gap: 1.5,
    px: 2,
    py: 1,
    cursor: "pointer",
    borderRadius: "6px",
    mx: 0.5,
    fontSize: "0.875rem",
    color: "rgba(255,255,255,0.7)",
    fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
    transition: "background 0.1s ease, color 0.1s ease",
    justifyContent: "space-between",
    '&[aria-selected="true"], &[data-selected="true"]': {
      bgcolor: "rgba(59,137,255,0.12)",
      color: "#3b89ff",
      "& .cmd-icon": { color: "#3b89ff" },
    },
    "&:hover": {
      bgcolor: "rgba(59,137,255,0.08)",
      color: "#3b89ff",
      "& .cmd-icon": { color: "#3b89ff" },
    },
  };

  const iconSx = {
    fontSize: "1.1rem",
    color: "rgba(255,255,255,0.4)",
    flexShrink: 0,
    transition: "color 0.1s ease",
  };

  const hintSx = {
    fontSize: "0.7rem",
    color: "rgba(255,255,255,0.25)",
    fontFamily: "var(--font-geist-mono)",
    flexShrink: 0,
  };

  const emptySx = {
    px: 2,
    py: 3,
    textAlign: "center" as const,
    fontSize: "0.8rem",
    color: "rgba(255,255,255,0.3)",
    fontFamily: "var(--font-geist-mono)",
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth={false}
      PaperProps={{ sx: { bgcolor: "transparent", boxShadow: "none", m: 2, width: "100%", maxWidth: 560 } }}
      slotProps={{ backdrop: { sx: { bgcolor: "rgba(0,0,0,0.65)", backdropFilter: "blur(4px)" } } }}
    >
      <Box sx={containerSx}>
        <Command
          label="Command Palette"
          shouldFilter={false}
          onKeyDown={(e: React.KeyboardEvent) => {
            if (e.key === "Escape") handleClose();
          }}
        >
          <Box sx={inputWrapperSx}>
            <SearchIcon sx={{ ...iconSx, color: "rgba(255,255,255,0.3)", fontSize: "1.15rem" }} />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Search commands..."
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                fontFamily: "var(--font-geist-mono)",
                fontSize: "0.9rem",
                color: "rgba(255,255,255,0.9)",
                caretColor: "#3b89ff",
              }}
            />
            <Box sx={badgeSx}>⌘K</Box>
          </Box>

          <Box sx={listSx}>
            <Command.List>
              <Command.Group>
                <Box component="span" sx={groupLabelSx}>Tickers</Box>
                {loading && (
                  <Box sx={emptySx}>Searching...</Box>
                )}
                {!loading && query.trim() && results.length === 0 && (
                  <Command.Empty>
                    <Box sx={emptySx}>No results found for &quot;{query}&quot;</Box>
                  </Command.Empty>
                )}
                {!loading && results.map((r) => (
                  <Command.Item
                    key={r.ticker}
                    value={`ticker-${r.ticker}`}
                    onSelect={() => {
                      scrollToSection("overview");
                    }}
                  >
                    <Box sx={itemSx} component="div">
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        <Box sx={dotSx(r.has_data)} />
                        <Box
                          component="span"
                          sx={{
                            fontFamily: "var(--font-geist-mono)",
                            fontSize: "0.875rem",
                            fontWeight: 600,
                            color: "inherit",
                          }}
                        >
                          {r.ticker}
                        </Box>
                        <Box
                          component="span"
                          sx={{
                            fontSize: "0.75rem",
                            color: r.has_data ? "rgba(54,187,128,0.8)" : "rgba(255,255,255,0.3)",
                            fontFamily: "var(--font-geist-mono)",
                          }}
                        >
                          {r.has_data ? "has data" : "no data"}
                        </Box>
                      </Box>
                      <Box sx={hintSx}>↵</Box>
                    </Box>
                  </Command.Item>
                ))}
              </Command.Group>

              <Box
                component="hr"
                sx={{
                  border: "none",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                  my: 0.5,
                  mx: 1,
                }}
              />

              <Command.Group>
                <Box component="span" sx={groupLabelSx}>Sections</Box>
                {SECTIONS.map((section) => {
                  const Icon = section.icon;
                  return (
                    <Command.Item
                      key={section.id}
                      value={`section-${section.id}`}
                      onSelect={() => scrollToSection(section.id)}
                    >
                      <Box sx={itemSx} component="div">
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                          <Icon className="cmd-icon" sx={iconSx} />
                          <Box component="span">{section.label}</Box>
                        </Box>
                        <Box sx={hintSx}>↵</Box>
                      </Box>
                    </Command.Item>
                  );
                })}
                <Command.Item
                  key="portfolio"
                  value="section-portfolio"
                  onSelect={navigatePortfolio}
                >
                  <Box sx={itemSx} component="div">
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                      <AccountBalanceWalletIcon className="cmd-icon" sx={iconSx} />
                      <Box component="span">Portfolio</Box>
                    </Box>
                    <Box sx={hintSx}>↵</Box>
                  </Box>
                </Command.Item>
              </Command.Group>

              <Box
                component="hr"
                sx={{
                  border: "none",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                  my: 0.5,
                  mx: 1,
                }}
              />

              <Command.Group>
                <Box component="span" sx={groupLabelSx}>Settings</Box>
                <Command.Item
                  value="settings-toggle-theme"
                  onSelect={handleToggleTheme}
                >
                  <Box sx={itemSx} component="div">
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                      {mode === "dark" ? (
                        <LightModeIcon className="cmd-icon" sx={iconSx} />
                      ) : (
                        <DarkModeIcon className="cmd-icon" sx={iconSx} />
                      )}
                      <Box component="span">
                        {mode === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
                      </Box>
                    </Box>
                    <Box sx={hintSx}>↵</Box>
                  </Box>
                </Command.Item>
              </Command.Group>
            </Command.List>
          </Box>

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              px: 2,
              py: 1,
              borderTop: "1px solid rgba(255,255,255,0.06)",
              bgcolor: "rgba(0,0,0,0.2)",
            }}
          >
            {[
              { key: "↑↓", label: "navigate" },
              { key: "↵", label: "select" },
              { key: "esc", label: "close" },
            ].map(({ key, label }) => (
              <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Box
                  component="span"
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    fontSize: "0.65rem",
                    color: "rgba(255,255,255,0.35)",
                    bgcolor: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "4px",
                    px: 0.5,
                    py: 0.125,
                  }}
                >
                  {key}
                </Box>
                <Box
                  component="span"
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    fontSize: "0.65rem",
                    color: "rgba(255,255,255,0.2)",
                  }}
                >
                  {label}
                </Box>
              </Box>
            ))}
          </Box>
        </Command>
      </Box>
    </Dialog>
  );
}
