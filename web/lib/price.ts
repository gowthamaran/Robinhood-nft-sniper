/**
 * Current ETH/USD, used only to render a secondary USD figure next to the
 * primary ETH values. If it is unavailable the UI simply shows ETH.
 */
let cached: { value: number; at: number } | null = null;
const TTL_MS = 10 * 60 * 1000;

export async function ethUsdRate(): Promise<number | null> {
  if (cached && Date.now() - cached.at < TTL_MS) return cached.value;
  try {
    const res = await fetch(
      "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
      { signal: AbortSignal.timeout(4_000) },
    );
    if (!res.ok) return cached?.value ?? null;
    const json = (await res.json()) as { ethereum?: { usd?: number } };
    const value = json?.ethereum?.usd;
    if (typeof value === "number" && value > 0) {
      cached = { value, at: Date.now() };
      return value;
    }
  } catch {
    /* fall through to whatever we already had */
  }
  return cached?.value ?? null;
}
