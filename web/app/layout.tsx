import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter, Space_Grotesk } from "next/font/google";
import { siteOrigin } from "@/lib/format";
import "./globals.css";

const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-display" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-mono" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: {
    default: "Fumbled.lol — How Much Did Your NFT Wallet Fumble?",
    template: "%s | Fumbled.lol",
  },
  description:
    "Paste a wallet and see what it actually made and lost on NFTs: realised profit, realised loss, win rate, best and worst trade, and the upside you fumbled by selling early.",
  robots: "index, follow",
  openGraph: {
    title: "How Much Did Your NFT Wallet Fumble?",
    description: "A public, read-only NFT wallet autopsy. Real numbers, no wallet connection.",
    siteName: "Fumbled.lol",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "How Much Did Your NFT Wallet Fumble?",
    description: "A public, read-only NFT wallet autopsy. Real numbers, no wallet connection.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
