/**
 * Minimal OpenSea API v2 client.
 *
 * Everything here is defensive on purpose: the upstream shapes vary between
 * event types and we would rather report a value as UNAVAILABLE than invent it.
 */

const BASE = "https://api.opensea.io/api/v2";

const KEY_NAMES = ["OPENSEA_API_KEY", "OPENSEA_KEY", "OPENSEA_TOKEN"];

export function openseaKey(): string | null {
  for (const name of KEY_NAMES) {
    const value = process.env[name];
    if (value && value.trim()) return value.trim();
  }
  return null;
}

export type UpstreamCall = { path: string; status: number; ms: number; items?: number };

export class Upstream {
  readonly calls: UpstreamCall[] = [];
  private readonly key: string;
  private budgetMs: number;
  private readonly startedAt = Date.now();
  rateLimited = false;

  constructor(key: string, budgetMs = 18_000) {
    this.key = key;
    this.budgetMs = budgetMs;
  }

  get exhausted(): boolean {
    return Date.now() - this.startedAt > this.budgetMs;
  }

  /** True once at least one upstream call actually came back OK. */
  get reachable(): boolean {
    return this.calls.some((call) => call.status >= 200 && call.status < 300);
  }

  async get<T>(path: string): Promise<T | null> {
    if (this.exhausted) return null;
    const started = Date.now();
    try {
      const res = await fetch(`${BASE}${path}`, {
        headers: { "x-api-key": this.key, accept: "application/json" },
        signal: AbortSignal.timeout(9_000),
        cache: "no-store",
      });
      const call: UpstreamCall = { path, status: res.status, ms: Date.now() - started };
      this.calls.push(call);
      if (res.status === 429) {
        this.rateLimited = true;
        return null;
      }
      if (!res.ok) return null;
      return (await res.json()) as T;
    } catch {
      this.calls.push({ path, status: 0, ms: Date.now() - started });
      return null;
    }
  }
}

export type OsPayment = {
  quantity?: string | number;
  token_address?: string;
  decimals?: number | string;
  symbol?: string;
};

export type OsNft = {
  identifier?: string;
  collection?: string;
  contract?: string;
  name?: string | null;
  image_url?: string | null;
  display_image_url?: string | null;
};

export type OsEvent = {
  event_type?: string;
  chain?: string;
  quantity?: number;
  nft?: OsNft;
  asset?: OsNft;
  seller?: string;
  buyer?: string;
  from_address?: string;
  to_address?: string;
  payment?: OsPayment;
  event_timestamp?: number | string;
  closing_date?: number;
  transaction?: string;
};

type EventsPage = { asset_events?: OsEvent[]; next?: string | null };

/**
 * Pull account events newest-first, following `next` cursors until we run out
 * of pages, hit `maxEvents`, or run out of time budget.
 */
export async function fetchAccountEvents(
  up: Upstream,
  address: string,
  maxEvents: number,
  maxPages: number,
): Promise<{ events: OsEvent[]; truncated: boolean }> {
  const events: OsEvent[] = [];
  let cursor: string | null = null;
  let truncated = false;

  for (let page = 0; page < maxPages; page += 1) {
    const params = new URLSearchParams({ chain: "ethereum", limit: "50" });
    params.append("event_type", "sale");
    params.append("event_type", "transfer");
    if (cursor) params.set("next", cursor);

    const data: EventsPage | null = await up.get<EventsPage>(
      `/events/accounts/${address}?${params.toString()}`,
    );
    if (!data) {
      truncated = events.length > 0;
      break;
    }
    const batch = Array.isArray(data.asset_events) ? data.asset_events : [];
    events.push(...batch);
    const last = up.calls[up.calls.length - 1];
    if (last) last.items = batch.length;

    cursor = data.next ?? null;
    if (!cursor || batch.length === 0) break;
    if (events.length >= maxEvents) {
      truncated = true;
      break;
    }
    if (up.exhausted) {
      truncated = true;
      break;
    }
  }

  return { events: events.slice(0, maxEvents), truncated };
}

export type OsHolding = {
  identifier?: string;
  collection?: string;
  contract?: string;
  name?: string | null;
  image_url?: string | null;
  display_image_url?: string | null;
};

type NftsPage = { nfts?: OsHolding[]; next?: string | null };

export async function fetchHoldings(
  up: Upstream,
  address: string,
  maxItems: number,
  maxPages: number,
): Promise<OsHolding[]> {
  const out: OsHolding[] = [];
  let cursor: string | null = null;

  for (let page = 0; page < maxPages; page += 1) {
    const params = new URLSearchParams({ limit: "200" });
    if (cursor) params.set("next", cursor);
    const data: NftsPage | null = await up.get<NftsPage>(
      `/chain/ethereum/account/${address}/nfts?${params.toString()}`,
    );
    if (!data) break;
    const batch = Array.isArray(data.nfts) ? data.nfts : [];
    out.push(...batch);
    const last = up.calls[up.calls.length - 1];
    if (last) last.items = batch.length;
    cursor = data.next ?? null;
    if (!cursor || batch.length === 0 || out.length >= maxItems || up.exhausted) break;
  }
  return out.slice(0, maxItems);
}

type StatsResponse = {
  total?: { floor_price?: number | string | null; floor_price_symbol?: string | null };
};

/** Current floor price in ETH for a collection slug, or null when not defensible. */
export async function fetchFloor(up: Upstream, slug: string): Promise<number | null> {
  const data = await up.get<StatsResponse>(`/collections/${encodeURIComponent(slug)}/stats`);
  const raw = data?.total?.floor_price;
  const symbol = data?.total?.floor_price_symbol;
  if (raw === null || raw === undefined) return null;
  const value = typeof raw === "string" ? Number(raw) : raw;
  if (!Number.isFinite(value) || value <= 0) return null;
  // Only trust ETH-denominated floors; anything else would need a rate we do not have.
  if (symbol && !["ETH", "WETH"].includes(symbol.toUpperCase())) return null;
  return value;
}
