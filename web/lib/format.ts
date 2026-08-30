import type { Autopsy } from "./types";

export const SITE_NAME = "Fumbled.lol";

/** Canonical origin, used for share links and OG image URLs. */
export function siteOrigin(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_ORIGIN;
  if (explicit) return explicit.replace(/\/$/, "");
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return `https://${vercel}`;
  return "https://fumbled-lol.vercel.app";
}

export function isAddress(value: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(value.trim());
}

export function shortAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function formatEth(value: number | null, dp = 2): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const decimals = abs >= 100 ? 0 : abs >= 1 ? dp : 3;
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatUsd(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(abs >= 10_000 ? 0 : 1)}K`;
  return `$${value.toFixed(0)}`;
}

export function usdOf(ethValue: number | null, ethUsd: number | null): number | null {
  if (ethValue === null || ethUsd === null) return null;
  return ethValue * ethUsd;
}

export function formatMetric(value: number | null, unit: string): string {
  if (value === null) return "NO DATA";
  if (unit === "%") return `${Math.round(value)}`;
  if (unit === "COUNT") return `${Math.round(value)}`;
  return formatEth(value);
}

/** The line people actually paste into X. Numbers first, brand last. */
export function buildShareText(data: Autopsy): string {
  const made = data.made.value;
  const lost = data.lost.value;
  const net = data.net.value;

  const lines: string[] = [];

  if (net !== null && made !== null && lost !== null) {
    const verb = net >= 0 ? "up" : "down";
    lines.push(
      `My NFT wallet is ${verb} ${formatEth(Math.abs(net))} ETH. (+${formatEth(made)} made / -${formatEth(
        lost,
      )} lost)`,
    );
  } else {
    lines.push("I ran my wallet through an NFT autopsy.");
  }

  if (data.fumbled.value !== null && data.fumbled.value > 0) {
    lines.push(`I fumbled ${formatEth(data.fumbled.value)} ETH by selling too early.`);
  }

  lines.push(`NFT IQ: ${data.nftIq}/100 — ${data.personality}.`);
  lines.push("");
  lines.push("Check yours:");

  return lines.join("\n");
}

export function shareUrl(address: string): string {
  return `${siteOrigin()}/wallet/${address}`;
}

export function tweetIntent(data: Autopsy): string {
  const text = buildShareText(data);
  const params = new URLSearchParams({ text, url: shareUrl(data.address) });
  return `https://x.com/intent/post?${params.toString()}`;
}
