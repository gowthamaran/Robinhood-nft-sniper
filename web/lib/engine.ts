import {
  Upstream,
  fetchAccountEvents,
  fetchFloor,
  fetchHoldings,
  type OsEvent,
  type OsNft,
} from "./opensea";
import type { Autopsy, Confidence, FumbleCard, Metric, TradeCard } from "./types";

const ZERO = "0x0000000000000000000000000000000000000000";
const ETH_LIKE = new Set(["ETH", "WETH"]);
const DAY = 86_400;
const FLIP_WINDOW_DAYS = 7;

export const MAX_EVENTS = 1_000;
export const MAX_EVENT_PAGES = 20;
export const MAX_HOLDINGS = 200;

/* ------------------------------------------------------------------ */
/* Normalisation                                                       */
/* ------------------------------------------------------------------ */

function toSeconds(value: number | string | undefined): number | null {
  if (value === undefined || value === null) return null;
  if (typeof value === "number") return value > 1e12 ? Math.floor(value / 1000) : Math.floor(value);
  const asNumber = Number(value);
  if (Number.isFinite(asNumber) && asNumber > 0) {
    return asNumber > 1e12 ? Math.floor(asNumber / 1000) : Math.floor(asNumber);
  }
  const parsed = Date.parse(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);
  return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : null;
}

/** Payment amount expressed in ETH, or null when the currency is not ETH-like. */
function paymentEth(event: OsEvent): number | null {
  const payment = event.payment;
  if (!payment) return null;
  const symbol = (payment.symbol ?? "").toUpperCase();
  if (symbol && !ETH_LIKE.has(symbol)) return null;
  if (!symbol && payment.token_address && payment.token_address !== ZERO) return null;

  const rawQuantity = payment.quantity;
  if (rawQuantity === undefined || rawQuantity === null) return null;
  const decimals = Number(payment.decimals ?? 18);
  const quantity = Number(rawQuantity);
  if (!Number.isFinite(quantity) || !Number.isFinite(decimals)) return null;

  const value = quantity / 10 ** decimals;
  if (!Number.isFinite(value) || value < 0) return null;
  // Guard against absurd values from malformed upstream records.
  if (value > 1_000_000) return null;
  return value;
}

function nftOf(event: OsEvent): OsNft | null {
  return event.nft ?? event.asset ?? null;
}

function tokenKey(nft: OsNft | null): string | null {
  if (!nft) return null;
  const contract = (nft.contract ?? "").toLowerCase();
  const id = nft.identifier ?? "";
  if (!contract || !id) return null;
  return `${contract}:${id}`;
}

function imageOf(nft: OsNft | null): string | null {
  const url = nft?.display_image_url ?? nft?.image_url ?? null;
  if (!url) return null;
  // Only ever render https images; never data:/javascript: from upstream metadata.
  return /^https:\/\//i.test(url) ? url : null;
}

function displayName(nft: OsNft | null): string {
  const name = (nft?.name ?? "").trim();
  if (name) return name.slice(0, 80);
  const id = nft?.identifier;
  return id ? `#${String(id).slice(0, 20)}` : "UNTITLED";
}

function collectionOf(nft: OsNft | null): { label: string; slug: string | null } {
  const slug = (nft?.collection ?? "").trim() || null;
  if (!slug) return { label: "UNKNOWN COLLECTION", slug: null };
  const label = slug.replace(/[-_]+/g, " ").toUpperCase().slice(0, 60);
  return { label, slug };
}

/* ------------------------------------------------------------------ */
/* Ledger                                                              */
/* ------------------------------------------------------------------ */

type Acquisition = {
  at: number;
  costEth: number | null;
  kind: "BUY" | "MINT" | "TRANSFER_IN";
  nft: OsNft | null;
};

type ClosedTrade = {
  key: string;
  nft: OsNft | null;
  boughtEth: number | null;
  soldEth: number;
  pnlEth: number | null;
  acquiredAt: number | null;
  soldAt: number;
  kind: Acquisition["kind"];
};

type Disposal = {
  key: string;
  nft: OsNft | null;
  soldEth: number;
  soldAt: number;
};

type Ledger = {
  closed: ClosedTrade[];
  disposals: Disposal[];
  mintsAcquired: number;
  buysSeen: number;
  salesSeen: number;
  earliest: number | null;
};

/**
 * Walk events oldest-first and FIFO-match disposals against acquisitions of the
 * same token. An acquisition with no defensible cost (mint, airdrop, plain
 * transfer in) never receives an invented zero cost basis - the disposal is
 * still recorded, but its P&L stays null.
 */
export function buildLedger(events: OsEvent[], address: string): Ledger {
  const me = address.toLowerCase();
  const lots = new Map<string, Acquisition[]>();
  const closed: ClosedTrade[] = [];
  const disposals: Disposal[] = [];
  let mintsAcquired = 0;
  let buysSeen = 0;
  let salesSeen = 0;
  let earliest: number | null = null;

  const ordered = events
    .map((event) => ({ event, at: toSeconds(event.event_timestamp ?? event.closing_date) }))
    .filter((entry): entry is { event: OsEvent; at: number } => entry.at !== null)
    .sort((a, b) => a.at - b.at);

  for (const { event, at } of ordered) {
    if (earliest === null || at < earliest) earliest = at;

    const nft = nftOf(event);
    const key = tokenKey(nft);
    if (!key) continue;

    const type = (event.event_type ?? "").toLowerCase();
    const seller = (event.seller ?? "").toLowerCase();
    const buyer = (event.buyer ?? "").toLowerCase();
    const from = (event.from_address ?? "").toLowerCase();
    const to = (event.to_address ?? "").toLowerCase();

    if (type === "sale") {
      const price = paymentEth(event);

      if (buyer === me) {
        buysSeen += 1;
        const queue = lots.get(key) ?? [];
        queue.push({ at, costEth: price, kind: "BUY", nft });
        lots.set(key, queue);
        continue;
      }

      if (seller === me) {
        salesSeen += 1;
        if (price === null) continue;
        disposals.push({ key, nft, soldEth: price, soldAt: at });

        const queue = lots.get(key) ?? [];
        const lot = queue.shift();
        lots.set(key, queue);

        closed.push({
          key,
          nft,
          boughtEth: lot?.costEth ?? null,
          soldEth: price,
          pnlEth: lot && lot.costEth !== null ? price - lot.costEth : null,
          acquiredAt: lot?.at ?? null,
          soldAt: at,
          kind: lot?.kind ?? "TRANSFER_IN",
        });
      }
      continue;
    }

    if (type === "transfer" || type === "mint") {
      if (to === me) {
        const isMint = from === ZERO || type === "mint";
        if (isMint) mintsAcquired += 1;
        const queue = lots.get(key) ?? [];
        queue.push({ at, costEth: null, kind: isMint ? "MINT" : "TRANSFER_IN", nft });
        lots.set(key, queue);
      } else if (from === me) {
        // Transferred out with no sale price: consume the lot so a later FIFO
        // match cannot pair the wrong acquisition, but record no proceeds.
        const queue = lots.get(key) ?? [];
        queue.shift();
        lots.set(key, queue);
      }
    }
  }

  return { closed, disposals, mintsAcquired, buysSeen, salesSeen, earliest };
}

/* ------------------------------------------------------------------ */
/* Metrics                                                             */
/* ------------------------------------------------------------------ */

function metric(
  label: string,
  value: number | null,
  unit: Metric["unit"],
  confidence: Confidence,
  note: string,
): Metric {
  return { label, value, unit, confidence, note };
}

function round(value: number, dp = 4): number {
  const factor = 10 ** dp;
  return Math.round(value * factor) / factor;
}

function toCard(trade: ClosedTrade): TradeCard {
  const collection = collectionOf(trade.nft);
  const heldDays =
    trade.acquiredAt !== null ? Math.max(0, Math.round((trade.soldAt - trade.acquiredAt) / DAY)) : null;
  return {
    collection: collection.label,
    collectionSlug: collection.slug,
    name: displayName(trade.nft),
    imageUrl: imageOf(trade.nft),
    boughtEth: trade.boughtEth === null ? null : round(trade.boughtEth),
    soldEth: round(trade.soldEth),
    pnlEth: round(trade.pnlEth ?? 0),
    pnlPct:
      trade.boughtEth && trade.boughtEth > 0 && trade.pnlEth !== null
        ? Math.round((trade.pnlEth / trade.boughtEth) * 100)
        : null,
    heldDays,
    soldAt: trade.soldAt,
  };
}

export function scoreIq(input: {
  netEth: number;
  madeEth: number;
  lostEth: number;
  winRate: number | null;
  closedCount: number;
}): number {
  const { netEth, madeEth, lostEth, winRate, closedCount } = input;

  // Profitability: net as a share of everything that moved through the wallet.
  const turnover = madeEth + lostEth;
  const profitability = turnover > 0 ? clamp((netEth / turnover) * 50 + 50, 0, 100) : 50;
  const win = winRate === null ? 50 : clamp(winRate, 0, 100);

  let score = 0.6 * profitability + 0.4 * win;

  // A wallet with almost no closed trades has not earned a strong opinion.
  if (closedCount < 3) score = score * 0.5 + 50 * 0.5;

  return Math.round(clamp(score, 0, 100));
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function personalityFor(input: {
  iq: number;
  netEth: number;
  closedCount: number;
  flipCount: number;
  holdingsCount: number;
  winRate: number | null;
}): { personality: string; verdict: string } {
  const { iq, netEth, closedCount, flipCount, holdingsCount, winRate } = input;

  if (closedCount === 0 && holdingsCount === 0) {
    return {
      personality: "GHOST WALLET",
      verdict: "no NFT trades on record. the safest portfolio is the one you never opened.",
    };
  }
  if (closedCount === 0) {
    return {
      personality: "PURE HOPIUM",
      verdict: "you have never closed a trade. every bag is still theoretically a winner.",
    };
  }
  if (netEth <= -5) {
    return {
      personality: "EXIT LIQUIDITY",
      verdict: "you were the reason someone else's chart went up.",
    };
  }
  if (netEth < 0 && flipCount > closedCount * 0.5) {
    return {
      personality: "SPEEDRUN LOSER",
      verdict: "you lost money faster than most people can read a floor price.",
    };
  }
  if (netEth < 0) {
    return { personality: "TUITION PAYER", verdict: "expensive lessons, no diploma." };
  }
  if (iq >= 85 && netEth >= 10) {
    return { personality: "SILENT ASSASSIN", verdict: "you have been quietly farming everyone else." };
  }
  if (flipCount > closedCount * 0.6) {
    return { personality: "SERIAL FLIPPER", verdict: "you have never held anything long enough to love it." };
  }
  if (winRate !== null && winRate >= 70) {
    return { personality: "SNIPER", verdict: "annoyingly good at this, and you know it." };
  }
  if (holdingsCount > closedCount * 3) {
    return { personality: "BAG COLLECTOR", verdict: "diamond hands sold separately." };
  }
  return { personality: "MID CURVE", verdict: "up money and still somehow not happy about it." };
}

/* ------------------------------------------------------------------ */
/* Orchestration                                                       */
/* ------------------------------------------------------------------ */

export type BuildOptions = { ethUsd: number | null };

export async function buildAutopsy(
  up: Upstream,
  address: string,
  options: BuildOptions,
): Promise<Autopsy> {
  const [{ events, truncated }, holdings] = await Promise.all([
    fetchAccountEvents(up, address, MAX_EVENTS, MAX_EVENT_PAGES),
    fetchHoldings(up, address, MAX_HOLDINGS, 2),
  ]);

  const ledger = buildLedger(events, address);
  const priced = ledger.closed.filter(
    (trade): trade is ClosedTrade & { pnlEth: number } => trade.pnlEth !== null,
  );

  const madeEth = priced.filter((t) => t.pnlEth > 0).reduce((sum, t) => sum + t.pnlEth, 0);
  const lostEth = Math.abs(priced.filter((t) => t.pnlEth < 0).reduce((sum, t) => sum + t.pnlEth, 0));
  const netEth = madeEth - lostEth;

  const wins = priced.filter((t) => t.pnlEth > 0).length;
  const losses = priced.filter((t) => t.pnlEth < 0).length;
  const winRate = priced.length > 0 ? Math.round((wins / priced.length) * 100) : null;

  const flips = priced.filter(
    (t) => t.acquiredAt !== null && (t.soldAt - t.acquiredAt) / DAY <= FLIP_WINDOW_DAYS,
  );
  const flipPnl = flips.reduce((sum, t) => sum + t.pnlEth, 0);

  // Mint performance: proceeds from tokens this wallet minted and later sold.
  const mintSales = ledger.closed.filter((t) => t.kind === "MINT");
  const mintProceeds = mintSales.reduce((sum, t) => sum + t.soldEth, 0);

  const sortedByPnl = [...priced].sort((a, b) => b.pnlEth - a.pnlEth);
  const bestTrade = sortedByPnl.length > 0 && sortedByPnl[0].pnlEth > 0 ? toCard(sortedByPnl[0]) : null;
  const last = sortedByPnl[sortedByPnl.length - 1];
  const worstTrade = sortedByPnl.length > 0 && last.pnlEth < 0 ? toCard(last) : null;

  const fumble = await computeFumble(up, ledger.disposals);

  const holdingsCount = holdings.length;
  const iq = scoreIq({ netEth, madeEth, lostEth, winRate, closedCount: priced.length });
  const { personality, verdict } = personalityFor({
    iq,
    netEth,
    closedCount: priced.length,
    flipCount: flips.length,
    holdingsCount,
    winRate,
  });

  const hasTrades = priced.length > 0;
  const tradeNote = `Reconstructed from ${priced.length} FIFO-matched ETH trade${
    priced.length === 1 ? "" : "s"
  }.`;

  const topCollections = summariseCollections(priced);

  return {
    address,
    ens: null,
    source: "LIVE",
    generatedAt: new Date().toISOString(),
    ethUsd: options.ethUsd,

    made: metric(
      "MADE",
      hasTrades ? round(madeEth) : null,
      "ETH",
      hasTrades ? "VERIFIED" : "UNAVAILABLE",
      hasTrades ? `Gross profit across winning trades. ${tradeNote}` : "No closed ETH trades found.",
    ),
    lost: metric(
      "LOST",
      hasTrades ? round(lostEth) : null,
      "ETH",
      hasTrades ? "VERIFIED" : "UNAVAILABLE",
      hasTrades ? `Gross loss across losing trades. ${tradeNote}` : "No closed ETH trades found.",
    ),
    net: metric(
      "NET",
      hasTrades ? round(netEth) : null,
      "ETH",
      hasTrades ? "VERIFIED" : "UNAVAILABLE",
      hasTrades ? "Made minus lost. Gas and marketplace fees excluded." : "No closed ETH trades found.",
    ),
    fumbled: fumble.metric,
    holding: metric(
      "HOLDING",
      holdingsCount > 0 ? holdingsCount : null,
      "COUNT",
      holdingsCount > 0 ? "VERIFIED" : "UNAVAILABLE",
      holdingsCount > 0
        ? `${holdingsCount} NFT${holdingsCount === 1 ? "" : "s"} currently held on Ethereum.`
        : "No current Ethereum NFT holdings indexed.",
    ),
    minting: metric(
      "MINT TAKE",
      mintSales.length > 0 ? round(mintProceeds) : null,
      "ETH",
      mintSales.length > 0 ? "ESTIMATED" : "UNAVAILABLE",
      mintSales.length > 0
        ? `Proceeds from ${mintSales.length} minted NFT${
            mintSales.length === 1 ? "" : "s"
          } you later sold. Mint cost and gas excluded.`
        : "No minted NFTs were sold within coverage.",
    ),
    flipping: metric(
      "FLIPPING",
      flips.length > 0 ? round(flipPnl) : null,
      "ETH",
      flips.length > 0 ? "VERIFIED" : "UNAVAILABLE",
      flips.length > 0
        ? `P&L on ${flips.length} trade${flips.length === 1 ? "" : "s"} closed within ${FLIP_WINDOW_DAYS} days.`
        : `No trades closed within ${FLIP_WINDOW_DAYS} days.`,
    ),
    winRate: metric(
      "WIN RATE",
      winRate,
      "%",
      winRate === null ? "UNAVAILABLE" : "VERIFIED",
      winRate === null ? "No closed ETH trades found." : `${wins} up, ${losses} down.`,
    ),

    nftIq: iq,
    personality,
    verdict,
    shareLine: "",

    tradesClosed: priced.length,
    tradesWon: wins,
    tradesLost: losses,
    eventCount: events.length,
    holdingsCount,
    periodStart: ledger.earliest,
    truncated,

    bestTrade,
    worstTrade,
    biggestFumble: fumble.card,

    topCollections,
    limitations: buildLimitations(events.length, truncated, up.rateLimited),
  };
}

function summariseCollections(trades: (ClosedTrade & { pnlEth: number })[]) {
  const map = new Map<string, { collection: string; slug: string | null; pnlEth: number; trades: number }>();
  for (const trade of trades) {
    const { label, slug } = collectionOf(trade.nft);
    const existing = map.get(label) ?? { collection: label, slug, pnlEth: 0, trades: 0 };
    existing.pnlEth += trade.pnlEth;
    existing.trades += 1;
    map.set(label, existing);
  }
  return [...map.values()]
    .map((entry) => ({ ...entry, pnlEth: round(entry.pnlEth) }))
    .sort((a, b) => Math.abs(b.pnlEth) - Math.abs(a.pnlEth))
    .slice(0, 6);
}

/**
 * FUMBLED is measured against today's floor: for each NFT this wallet sold,
 * how much more it would fetch at the collection's current floor. It is
 * hypothetical missed upside, never a realised loss.
 */
async function computeFumble(
  up: Upstream,
  disposals: Disposal[],
): Promise<{ metric: Metric; card: FumbleCard | null }> {
  const unavailable = metric(
    "FUMBLED",
    null,
    "ETH",
    "UNAVAILABLE",
    "No sold collection had a defensible ETH floor to compare against.",
  );
  if (disposals.length === 0) {
    return {
      metric: metric("FUMBLED", null, "ETH", "UNAVAILABLE", "No sales found within coverage."),
      card: null,
    };
  }

  // Only the most-sold collections are worth spending upstream calls on.
  const bySlug = new Map<string, Disposal[]>();
  for (const disposal of disposals) {
    const slug = collectionOf(disposal.nft).slug;
    if (!slug) continue;
    const list = bySlug.get(slug) ?? [];
    list.push(disposal);
    bySlug.set(slug, list);
  }

  const ranked = [...bySlug.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 8);

  let total = 0;
  let compared = 0;
  let best: FumbleCard | null = null;

  for (const [slug, list] of ranked) {
    if (up.exhausted) break;
    const floor = await fetchFloor(up, slug);
    if (floor === null) continue;

    for (const disposal of list) {
      compared += 1;
      const missed = floor - disposal.soldEth;
      if (missed <= 0) continue;
      total += missed;
      if (!best || missed > best.missedEth) {
        const collection = collectionOf(disposal.nft);
        best = {
          collection: collection.label,
          collectionSlug: collection.slug,
          name: displayName(disposal.nft),
          imageUrl: imageOf(disposal.nft),
          soldEth: round(disposal.soldEth),
          floorEth: round(floor),
          missedEth: round(missed),
          soldAt: disposal.soldAt,
        };
      }
    }
  }

  if (compared === 0) return { metric: unavailable, card: null };

  return {
    metric: metric(
      "FUMBLED",
      round(total),
      "ETH",
      "ESTIMATED",
      `Across ${compared} sold NFT${
        compared === 1 ? "" : "s"
      }, this is what today's collection floor would pay above your sale price. Hypothetical, not a loss.`,
    ),
    card: best,
  };
}

function buildLimitations(eventCount: number, truncated: boolean, rateLimited: boolean): string[] {
  const notes = [
    `Covers ${eventCount} recent Ethereum event${eventCount === 1 ? "" : "s"} indexed by OpenSea.`,
    "Trades settled off OpenSea's index (some Blur and private sales) are not counted.",
    "Only ETH and WETH trades are paired; other currencies are skipped rather than guessed.",
    "Gas and marketplace fees are excluded, so realised P&L is gross.",
    "Transfers and mints never receive an invented zero cost basis.",
  ];
  if (truncated) {
    notes.push("History was truncated at the coverage limit, so older trades may be missing.");
  }
  if (rateLimited) {
    notes.push("OpenSea rate-limited part of this request; some values may be incomplete.");
  }
  return notes;
}
