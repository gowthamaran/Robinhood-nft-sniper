"use client";

import { useState } from "react";
import { formatEth, isAddress, shortAddress } from "@/lib/format";
import type { Autopsy } from "@/lib/types";

type Side = { data: Autopsy } | null;

export function BattleClient() {
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<{ left: Side; right: Side } | null>(null);

  async function fetchSide(address: string): Promise<Side> {
    const res = await fetch(`/api/wallet/${address}`);
    if (!res.ok) return null;
    return { data: (await res.json()) as Autopsy };
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const a = left.trim();
    const b = right.trim();
    if (!isAddress(a) || !isAddress(b)) {
      setError("BOTH SIDES NEED A VALID 0x ADDRESS.");
      return;
    }
    setError(null);
    setPending(true);
    setResult(null);
    try {
      const [one, two] = await Promise.all([fetchSide(a), fetchSide(b)]);
      if (!one || !two) {
        setError("ONE OF THOSE WALLETS COULD NOT BE READ. TRY AGAIN IN A MINUTE.");
      } else {
        setResult({ left: one, right: two });
      }
    } catch {
      setError("THE LAB LOST CONNECTION. TRY AGAIN.");
    } finally {
      setPending(false);
    }
  }

  const leftIq = result?.left?.data.nftIq ?? 0;
  const rightIq = result?.right?.data.nftIq ?? 0;

  return (
    <>
      <form className="battle-form" onSubmit={onSubmit} noValidate style={{ marginTop: 34 }}>
        <label className="sr-only" htmlFor="left">
          First wallet address
        </label>
        <input
          id="left"
          placeholder="0x... (you)"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={left}
          onChange={(event) => setLeft(event.target.value)}
        />
        <div className="battle-vs">VS</div>
        <label className="sr-only" htmlFor="right">
          Second wallet address
        </label>
        <input
          id="right"
          placeholder="0x... (your friend)"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={right}
          onChange={(event) => setRight(event.target.value)}
        />
        <button className="wallet-button" type="submit" disabled={pending}>
          {pending ? "READING BOTH..." : "FIGHT →"}
        </button>
      </form>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {result?.left && result?.right ? (
        <div className="battle-results" style={{ marginTop: 50 }}>
          <BattleSide data={result.left.data} winner={leftIq >= rightIq} />
          <BattleSide data={result.right.data} winner={rightIq > leftIq} />
        </div>
      ) : null}
    </>
  );
}

function BattleSide({ data, winner }: { data: Autopsy; winner: boolean }) {
  const net = data.net.value;
  return (
    <div className={`battle-side ${winner ? "winner" : ""}`}>
      <div className="kicker">{winner ? "WINNER" : "CASUALTY"}</div>
      <h2>{shortAddress(data.address)}</h2>
      <div className="battle-score">{data.nftIq}</div>
      <div className="metric-label" style={{ marginBottom: 14 }}>
        {data.personality}
      </div>
      <p style={{ fontFamily: "var(--font-mono), monospace", fontSize: 12, lineHeight: 1.8 }}>
        NET {net === null ? "—" : `${net >= 0 ? "+" : "−"}${formatEth(Math.abs(net))} ETH`}
        <br />
        MADE {data.made.value === null ? "—" : `${formatEth(data.made.value)} ETH`}
        <br />
        LOST {data.lost.value === null ? "—" : `${formatEth(data.lost.value)} ETH`}
        <br />
        WIN RATE {data.winRate.value === null ? "—" : `${Math.round(data.winRate.value)}%`}
        <br />
        CLOSED TRADES {data.tradesClosed}
      </p>
    </div>
  );
}
