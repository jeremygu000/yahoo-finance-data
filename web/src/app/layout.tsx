import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Box from "@mui/material/Box";
import "./globals.css";
import ThemeProvider from "@/components/ThemeProvider";
import PriceProvider from "@/components/PriceProvider";
import AlertToast from "@/components/AlertToast";
import CommandPalette from "@/components/CommandPalette";
import Sidebar from "@/components/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Market Terminal",
  description: "Financial market data dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <ThemeProvider>
          <PriceProvider>
            <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
              <Sidebar />
              <Box
                component="main"
                sx={{ flex: 1, overflowY: "auto", height: "100vh" }}
              >
                {children}
              </Box>
            </Box>
            <AlertToast />
            <CommandPalette />
          </PriceProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
