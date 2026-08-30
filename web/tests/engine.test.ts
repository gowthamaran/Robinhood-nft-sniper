import assert from "node:assert/strict";
import test from "node:test";
import { buildLedger, personalityFor, scoreIq } from "../lib/engine";
import type { OsEvent } from "../lib/opensea";

const ME = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const OTHER = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const ZERO = "0x0000000000000000000000000000000000000000";

function eth(amount: number) {
  return { quantity: String(Math.round(amount * 1e18)), decimals: 18, symbol: "ETH" };
}

function sale(opts: { at: number; id: string; buyer: string; seller: string; price: number }): OsEvent {
  return {
    event_type: "sale",
    event_timestamp: opts.at,
    seller: opts.seller,
    buyer: opts.buyer,
    payment: eth(opts.price),
    nft: { identifier: opts.id, contract: "0xc0ffee", collection: "cool-cats", name: `Cat ${opts.id}` },
  };
}

function transfer(opts: { at: number; id: string; from: string; to: string }): OsEvent {
  return {
    event_type: "transfer",
    event_timestamp: opts.at,
    from_address: opts.from,
    to_address: opts.to,
    nft: { identifier: opts.id, contract: "0xc0ffee", collection: "cool-cats", name: `Cat ${opts.id}` },
  };
}

test("pairs a buy and a sale into one priced trade", () => {
  const ledger = buildLedger(
    [
      sale({ at: 1000, id: "1", buyer: ME, seller: OTHER, price: 1 }),
      sale({ at: 2000, id: "1", buyer: OTHER, seller: ME, price: 3 }),
    ],
    ME,
  );
  assert.equal(ledger.closed.length, 1);
  assert.equal(ledger.closed[0].boughtEth, 1);
  assert.equal(ledger.closed[0].soldEth, 3);
  assert.equal(ledger.closed[0].pnlEth, 2);
});

test("records a loss when the sale is below cost", () => {
  const ledger = buildLedger(
    [
      sale({ at: 1000, id: "7", buyer: ME, seller: OTHER, price: 5 }),
      sale({ at: 2000, id: "7", buyer: OTHER, seller: ME, price: 1.5 }),
    ],
    ME,
  );
  assert.equal(ledger.closed[0].pnlEth, -3.5);
});

test("never invents a cost basis for a mint", () => {
  const ledger = buildLedger(
    [
      transfer({ at: 1000, id: "9", from: ZERO, to: ME }),
      sale({ at: 2000, id: "9", buyer: OTHER, seller: ME, price: 4 }),
    ],
    ME,
  );
  assert.equal(ledger.mintsAcquired, 1);
  assert.equal(ledger.closed.length, 1);
  assert.equal(ledger.closed[0].pnlEth, null, "mint P&L must stay unknown");
  assert.equal(ledger.closed[0].kind, "MINT");
  assert.equal(ledger.disposals.length, 1, "proceeds are still recorded");
});

test("matches lots FIFO when the same token is traded twice", () => {
  const ledger = buildLedger(
    [
      sale({ at: 1000, id: "3", buyer: ME, seller: OTHER, price: 1 }),
      sale({ at: 1500, id: "3", buyer: OTHER, seller: ME, price: 2 }),
      sale({ at: 2000, id: "3", buyer: ME, seller: OTHER, price: 10 }),
      sale({ at: 2500, id: "3", buyer: OTHER, seller: ME, price: 6 }),
    ],
    ME,
  );
  assert.equal(ledger.closed.length, 2);
  assert.equal(ledger.closed[0].pnlEth, 1);
  assert.equal(ledger.closed[1].pnlEth, -4);
});

test("orders events by timestamp regardless of input order", () => {
  const ledger = buildLedger(
    [
      sale({ at: 2000, id: "1", buyer: OTHER, seller: ME, price: 3 }),
      sale({ at: 1000, id: "1", buyer: ME, seller: OTHER, price: 1 }),
    ],
    ME,
  );
  assert.equal(ledger.closed[0].pnlEth, 2);
});

test("skips non-ETH currencies rather than guessing a rate", () => {
  const usdcSale: OsEvent = {
    event_type: "sale",
    event_timestamp: 2000,
    seller: ME,
    buyer: OTHER,
    payment: { quantity: "5000000", decimals: 6, symbol: "USDC" },
    nft: { identifier: "5", contract: "0xc0ffee", collection: "cool-cats" },
  };
  const ledger = buildLedger([sale({ at: 1000, id: "5", buyer: ME, seller: OTHER, price: 1 }), usdcSale], ME);
  assert.equal(ledger.closed.length, 0, "unpriceable sale must not close a trade");
});

test("a transfer out consumes the lot without inventing proceeds", () => {
  const ledger = buildLedger(
    [
      sale({ at: 1000, id: "4", buyer: ME, seller: OTHER, price: 2 }),
      transfer({ at: 1500, id: "4", from: ME, to: OTHER }),
    ],
    ME,
  );
  assert.equal(ledger.closed.length, 0);
  assert.equal(ledger.disposals.length, 0);
});

test("parses ISO timestamps", () => {
  const ledger = buildLedger(
    [
      { ...sale({ at: 0, id: "1", buyer: ME, seller: OTHER, price: 1 }), event_timestamp: "2024-01-01T00:00:00" },
      { ...sale({ at: 0, id: "1", buyer: OTHER, seller: ME, price: 4 }), event_timestamp: "2024-02-01T00:00:00" },
    ],
    ME,
  );
  assert.equal(ledger.closed.length, 1);
  assert.equal(ledger.closed[0].pnlEth, 3);
});

test("IQ is deterministic and bounded", () => {
  const a = scoreIq({ netEth: 10, madeEth: 12, lostEth: 2, winRate: 80, closedCount: 20 });
  const b = scoreIq({ netEth: 10, madeEth: 12, lostEth: 2, winRate: 80, closedCount: 20 });
  assert.equal(a, b);
  assert.ok(a >= 0 && a <= 100);
  const loser = scoreIq({ netEth: -10, madeEth: 1, lostEth: 11, winRate: 10, closedCount: 20 });
  assert.ok(loser < a, "a losing wallet must score below a winning one");
});

test("a thin history is pulled toward neutral", () => {
  const thin = scoreIq({ netEth: 5, madeEth: 5, lostEth: 0, winRate: 100, closedCount: 1 });
  const thick = scoreIq({ netEth: 5, madeEth: 5, lostEth: 0, winRate: 100, closedCount: 30 });
  assert.ok(thin < thick);
});

test("personality reflects the numbers", () => {
  assert.equal(
    personalityFor({ iq: 20, netEth: -12, closedCount: 9, flipCount: 1, holdingsCount: 3, winRate: 20 })
      .personality,
    "EXIT LIQUIDITY",
  );
  assert.equal(
    personalityFor({ iq: 50, netEth: 0, closedCount: 0, flipCount: 0, holdingsCount: 0, winRate: null })
      .personality,
    "GHOST WALLET",
  );
});
