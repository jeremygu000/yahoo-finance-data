"use client";

import { useState, useEffect, useRef } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import { searchTickers } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

interface TickerSearchProps {
  onSelect?: (ticker: string) => void;
}

export default function TickerSearch({ onSelect }: TickerSearchProps) {
  const [inputValue, setInputValue] = useState("");
  const [options, setOptions] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (inputValue.length < 1) {
      setOptions([]);
      return;
    }
    setLoading(true);
    timerRef.current = setTimeout(async () => {
      try {
        const res = await searchTickers(inputValue);
        setOptions(res.results);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [inputValue]);

  return (
    <Autocomplete<SearchResult>
      options={options}
      loading={loading}
      inputValue={inputValue}
      onInputChange={(_event, value) => setInputValue(value)}
      onChange={(_event, value) => {
        if (value && onSelect) {
          onSelect(value.ticker);
        }
      }}
      getOptionLabel={(option) => option.ticker}
      isOptionEqualToValue={(option, value) => option.ticker === value.ticker}
      filterOptions={(x) => x}
      noOptionsText={
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", fontFamily: "var(--font-geist-mono)" }}>
          {inputValue.length < 1 ? "Type to search..." : "No results"}
        </Typography>
      }
      loadingText={
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", fontFamily: "var(--font-geist-mono)" }}>
          Searching...
        </Typography>
      }
      renderOption={(props, option) => {
        const { key, ...restProps } = props as { key: React.Key } & React.HTMLAttributes<HTMLLIElement>;
        return (
          <Box
            key={key}
            component="li"
            {...restProps}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: "12px !important",
              py: "6px !important",
              cursor: "pointer",
              "&:hover, &.Mui-focused": {
                bgcolor: "rgba(59,137,255,0.12) !important",
              },
            }}
          >
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontWeight: 700,
                fontSize: "0.8rem",
                color: "rgba(255,255,255,0.85)",
                flex: 1,
              }}
            >
              {option.ticker}
            </Typography>
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: option.has_data ? "#36bb80" : "rgba(255,255,255,0.25)",
                flexShrink: 0,
              }}
              title={option.has_data ? "Data available" : "No data"}
            />
          </Box>
        );
      }}
      slotProps={{
        paper: {
          sx: {
            bgcolor: "#1a2744",
            border: "1px solid rgba(255,255,255,0.1)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            borderRadius: "8px",
            mt: 0.5,
            "& .MuiAutocomplete-noOptions, & .MuiAutocomplete-loading": {
              color: "rgba(255,255,255,0.4)",
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.75rem",
              py: 1.5,
            },
          },
        },
        listbox: {
          sx: {
            py: 0.5,
            "& .MuiAutocomplete-option": {
              minHeight: "unset",
            },
          },
        },
      }}
      sx={{ width: "100%" }}
      renderInput={(params) => (
        <TextField
          {...params}
          size="small"
          variant="outlined"
          placeholder="Search tickers..."
          slotProps={{
            input: {
              ...params.InputProps,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon
                    sx={{
                      fontSize: "1rem",
                      color: "rgba(255,255,255,0.4)",
                    }}
                  />
                </InputAdornment>
              ),
              endAdornment: (
                <>
                  {loading ? <CircularProgress size={14} sx={{ color: "rgba(255,255,255,0.4)" }} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            },
          }}
          sx={{
            "& .MuiOutlinedInput-root": {
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.8rem",
              color: "rgba(255,255,255,0.85)",
              borderRadius: "8px",
              "& fieldset": {
                borderColor: "rgba(255,255,255,0.15)",
              },
              "&:hover fieldset": {
                borderColor: "rgba(255,255,255,0.3)",
              },
              "&.Mui-focused fieldset": {
                borderColor: "rgba(59,137,255,0.6)",
                borderWidth: "1px",
              },
            },
            "& .MuiInputBase-input::placeholder": {
              color: "rgba(255,255,255,0.35)",
              opacity: 1,
            },
            "& .MuiInputAdornment-root": {
              color: "rgba(255,255,255,0.4)",
            },
          }}
        />
      )}
    />
  );
}
