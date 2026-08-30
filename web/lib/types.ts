export type Confidence = "VERIFIED" | "ESTIMATED" | "UNAVAILABLE";

export type Metric = {
  label: string;
  value: number | null;
  unit: "ETH" | "USD" | "%" | "COUNT";
  confidence: Confidence;
  note: string;
};

export type TradeCard = {
  collection: string;
  collectionSlug: string | null;
  name: string;
  imageUrl: string | null;
  boughtEth: number | null;
  soldEth: number;
  pnlEth: number;
  pnlPct: number | null;
  heldDays: number | null;
  soldAt: number;
};

export type FumbleCard = {
  collection: string;
  collectionSlug: string | null;
  name: string;
  imageUrl: string | null;
  soldEth: number;
  floorEth: number;
  missedEth: number;
  soldAt: number;
};

export type Autopsy = {
  address: string;
  ens: string | null;
  source: "LIVE" | "DEMO";
  generatedAt: string;
  ethUsd: number | null;

  made: Metric;
  lost: Metric;
  net: Metric;
  fumbled: Metric;
  holding: Metric;
  minting: Metric;
  flipping: Metric;
  winRate: Metric;

  nftIq: number;
  personality: string;
  verdict: string;
  shareLine: string;

  tradesClosed: number;
  tradesWon: number;
  tradesLost: number;
  eventCount: number;
  holdingsCount: number;
  periodStart: number | null;
  truncated: boolean;

  bestTrade: TradeCard | null;
  worstTrade: TradeCard | null;
  biggestFumble: FumbleCard | null;

  topCollections: { collection: string; slug: string | null; pnlEth: number; trades: number }[];
  limitations: string[];
};
