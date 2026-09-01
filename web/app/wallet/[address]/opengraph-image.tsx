import { ImageResponse } from "next/og";
import { loadAutopsy } from "@/lib/data";
import { formatEth, formatUsd, isAddress, shortAddress, usdOf } from "@/lib/format";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Fumbled.lol NFT wallet autopsy";

const INK = "#13130F";
const PAPER = "#F1EADB";
const ACID = "#F5D90A";
const UP = "#6EE7B7";
const DOWN = "#FF7A68";
const MUTED = "#F1EADB99";

export default async function Image({ params }: { params: Promise<{ address: string }> }) {
  const { address } = await params;

  if (!isAddress(address)) return card({ headline: "INVALID WALLET", sub: "That is not an Ethereum address." });

  const result = await loadAutopsy(address);
  if (!result.ok) {
    return card({ headline: "AUTOPSY PENDING", sub: shortAddress(address) });
  }

  const data = result.data;
  const net = data.net.value;
  const netUsd = usdOf(net, data.ethUsd);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: INK,
          color: PAPER,
          fontFamily: "sans-serif",
          padding: 56,
        }}
      >
        {/* header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 24,
            letterSpacing: 2,
            color: MUTED,
          }}
        >
          <div style={{ display: "flex" }}>{shortAddress(data.address)}</div>
          <div style={{ display: "flex", color: PAPER, fontWeight: 700 }}>
            FUMBLED<span style={{ color: "#E3432F" }}>.</span>LOL
          </div>
        </div>

        {/* the number */}
        <div style={{ display: "flex", flexDirection: "column", marginTop: 34 }}>
          <div style={{ display: "flex", fontSize: 26, letterSpacing: 3, color: MUTED }}>
            {net === null ? "NO CLOSED TRADES" : net >= 0 ? "NET REALISED PROFIT" : "NET REALISED LOSS"}
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 22,
              marginTop: 12,
              fontSize: net === null ? 84 : 132,
              fontWeight: 800,
              letterSpacing: -6,
              color: net === null ? PAPER : net >= 0 ? UP : DOWN,
            }}
          >
            <div style={{ display: "flex" }}>
              {net === null ? "UNTRADED" : `${net >= 0 ? "+" : "−"}${formatEth(Math.abs(net))} ETH`}
            </div>
            {netUsd !== null ? (
              <div style={{ display: "flex", fontSize: 40, color: MUTED, letterSpacing: 0 }}>
                {formatUsd(Math.abs(netUsd))}
              </div>
            ) : null}
          </div>
        </div>

        {/* made / lost / fumbled */}
        <div style={{ display: "flex", marginTop: 40, borderTop: `1px solid #F1EADB3D`, paddingTop: 26 }}>
          <Stat label="MADE" value={data.made.value === null ? "—" : `+${formatEth(data.made.value)}`} color={UP} />
          <Stat label="LOST" value={data.lost.value === null ? "—" : `−${formatEth(data.lost.value)}`} color={DOWN} />
          <Stat
            label="FUMBLED"
            value={data.fumbled.value === null ? "—" : formatEth(data.fumbled.value)}
            color={PAPER}
          />
          <Stat
            label="WIN RATE"
            value={data.winRate.value === null ? "—" : `${Math.round(data.winRate.value)}%`}
            color={PAPER}
          />
        </div>

        {/* verdict */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 30,
            marginTop: "auto",
            paddingTop: 28,
            borderTop: `1px solid #F1EADB3D`,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              width: 116,
              height: 116,
              borderRadius: 58,
              border: `3px solid ${ACID}`,
            }}
          >
            <div style={{ display: "flex", fontSize: 48, fontWeight: 800, color: ACID }}>{data.nftIq}</div>
            <div style={{ display: "flex", fontSize: 15, color: MUTED }}>NFT IQ</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div style={{ display: "flex", fontSize: 42, fontWeight: 800, color: ACID, letterSpacing: -1 }}>
              {data.personality}
            </div>
            <div style={{ display: "flex", fontSize: 28, color: PAPER, marginTop: 8 }}>
              {truncate(data.verdict, 74)}
            </div>
          </div>
        </div>
      </div>
    ),
    size,
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <div style={{ display: "flex", fontSize: 20, letterSpacing: 2, color: MUTED }}>{label}</div>
      <div style={{ display: "flex", fontSize: 54, fontWeight: 800, color, marginTop: 8, letterSpacing: -2 }}>
        {value}
      </div>
    </div>
  );
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

function card({ headline, sub }: { headline: string; sub: string }) {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: INK,
          color: PAPER,
          fontFamily: "sans-serif",
          padding: 72,
        }}
      >
        <div style={{ display: "flex", fontSize: 84, fontWeight: 800, letterSpacing: -3 }}>{headline}</div>
        <div style={{ display: "flex", fontSize: 32, color: MUTED, marginTop: 18 }}>{sub}</div>
        <div style={{ display: "flex", fontSize: 28, color: ACID, marginTop: 46 }}>FUMBLED.LOL</div>
      </div>
    ),
    size,
  );
}
