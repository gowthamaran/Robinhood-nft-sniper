import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Footer, Topbar } from "@/components/Chrome";
import { Mascot } from "@/components/Mascot";
import { ShareRail } from "@/components/ShareRail";
import { loadAutopsy } from "@/lib/data";
import {
  formatEth,
  formatMetric,
  formatUsd,
  isAddress,
  shortAddress,
  shareUrl,
  siteOrigin,
  tweetIntent,
  usdOf,
} from "@/lib/format";
import type { Autopsy, Metric } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

type Props = { params: Promise<{ address: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { address } = await params;
  if (!isAddress(address)) return { title: "Wallet not found" };

  const short = shortAddress(address);
  const result = await loadAutopsy(address);

  let description = `See the public NFT wallet autopsy for ${short}.`;
  if (result.ok) {
    const { net, made, lost } = result.data;
    if (net.value !== null && made.value !== null && lost.value !== null) {
      const verb = net.value >= 0 ? "up" : "down";
      description = `${short} is ${verb} ${formatEth(Math.abs(net.value))} ETH on NFTs — ${formatEth(
        made.value,
      )} made, ${formatEth(lost.value)} lost. NFT IQ ${result.data.nftIq}/100.`;
    }
  }

  const title = `${short} — NFT Wallet Autopsy`;
  const image = `${siteOrigin()}/wallet/${address}/opengraph-image`;

  return {
    title,
    description,
    robots: "noindex, follow",
    openGraph: {
      title,
      description,
      url: shareUrl(address),
      images: [{ url: image, width: 1200, height: 630, alt: "Fumbled.lol NFT wallet autopsy" }],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [image],
    },
  };
}

export default async function WalletPage({ params }: Props) {
  const { address } = await params;
  if (!isAddress(address)) notFound();

  return (
    <Suspense fallback={<LoadingScreen />}>
      <Result address={address} />
    </Suspense>
  );
}

function LoadingScreen() {
  return (
    <main>
      <Topbar />
      <section className="loading-screen">
        <div className="loading-copy">
          <div className="kicker">PUBLIC DATA / ZERO SIGNATURES</div>
          <h1>CHECKING YOUR NFT CAREER.</h1>
          <div className="loading-line" aria-live="polite">
            PAIRING BUYS WITH SALES...
          </div>
          <div className="loading-bar" />
        </div>
        <div className="loading-mascot">
          <div className="mascot-stage">
            <Mascot />
          </div>
        </div>
      </section>
    </main>
  );
}

async function Result({ address }: { address: string }) {
  const result = await loadAutopsy(address);

  if (!result.ok) {
    return (
      <main>
        <Topbar />
        <section className="error-page">
          <div className="error-code">
            {result.reason === "NOT_CONFIGURED" ? "503 / NO DATA SOURCE" : "502 / AUTOPSY FAILED"}
          </div>
          <h1>{result.reason === "NOT_CONFIGURED" ? "THE LAB IS CLOSED." : "THE BODY MOVED."}</h1>
          <p>
            {result.reason === "NOT_CONFIGURED"
              ? "This deployment has no OpenSea API key configured, so there is nothing honest to show."
              : "OpenSea did not answer in time. This usually clears up within a minute."}
          </p>
          <div>
            <Link className="button-link" href="/">
              BACK TO THE LAB
            </Link>
          </div>
        </section>
        <Footer />
      </main>
    );
  }

  return <Autopsied data={result.data} />;
}

function Autopsied({ data }: { data: Autopsy }) {
  const net = data.net.value;
  const netUsd = usdOf(net, data.ethUsd);
  const direction = net === null ? "flat" : net >= 0 ? "up" : "down";
  const pageUrl = shareUrl(data.address);
  const cardUrl = `${siteOrigin()}/wallet/${data.address}/opengraph-image`;

  return (
    <main className="result-shell">
      <Topbar />

      <section className="result-head">
        <div>
          <div className="kicker">NFT WALLET AUTOPSY</div>
          <p className="wallet-address">{data.address}</p>
        </div>
        <div className="personality-stamp">{data.personality}</div>
      </section>

      {/* The screenshot. Everything above the fold is designed to be cropped. */}
      <section className="scorecard-wrap">
        <div className="scorecard">
          <div className="scorecard-top">
            <span>{shortAddress(data.address)}</span>
            <span>FUMBLED.LOL</span>
          </div>

          <div className="scorecard-net">
            <div className="net-label">
              {direction === "down" ? "NET REALISED LOSS" : "NET REALISED PROFIT"}
            </div>
            <div className={`net-value ${direction}`}>
              {net === null ? (
                <span>NO CLOSED TRADES</span>
              ) : (
                <>
                  <span>
                    {net >= 0 ? "+" : "−"}
                    {formatEth(Math.abs(net))} ETH
                  </span>
                  {netUsd !== null ? <span className="net-usd">{formatUsd(Math.abs(netUsd))}</span> : null}
                </>
              )}
            </div>
          </div>

          <div className="split">
            <div className="split-cell">
              <span>MADE</span>
              <strong className="made">
                {data.made.value === null ? "—" : `+${formatEth(data.made.value)}`}
              </strong>
              <small>{data.tradesWon} winning trades</small>
            </div>
            <div className="split-cell">
              <span>LOST</span>
              <strong className="lost">
                {data.lost.value === null ? "—" : `−${formatEth(data.lost.value)}`}
              </strong>
              <small>{data.tradesLost} losing trades</small>
            </div>
            <div className="split-cell">
              <span>FUMBLED</span>
              <strong>{data.fumbled.value === null ? "—" : formatEth(data.fumbled.value)}</strong>
              <small>{data.fumbled.value === null ? "not computable" : "vs today's floor"}</small>
            </div>
          </div>

          <div className="scorecard-verdict">
            <div className="iq-badge">
              <div>
                <strong>{data.nftIq}</strong>
                <span>NFT IQ</span>
              </div>
            </div>
            <div className="verdict-text">
              <b>{data.personality}</b>
              <p>{data.verdict}</p>
            </div>
          </div>

          <div className="scorecard-foot">
            <span>{data.tradesClosed} CLOSED TRADES</span>
            <span>
              WIN RATE {data.winRate.value === null ? "—" : `${Math.round(data.winRate.value)}%`}
            </span>
          </div>
        </div>

        <ShareRail tweetHref={tweetIntent(data)} pageUrl={pageUrl} cardUrl={cardUrl} />
      </section>

      <section className="mini-metrics">
        <MiniMetric metric={data.fumbled} ethUsd={data.ethUsd} />
        <MiniMetric metric={data.flipping} ethUsd={data.ethUsd} signed />
        <MiniMetric metric={data.minting} ethUsd={data.ethUsd} />
        <MiniMetric metric={data.winRate} ethUsd={data.ethUsd} />
        <MiniMetric metric={data.holding} ethUsd={data.ethUsd} />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>BEST &amp; WORST</h2>
          <p>
            The single trade that saved your year, and the one that did not. Both are FIFO-matched against a
            real purchase price.
          </p>
        </div>
        <div className="trade-grid">
          <TradeSide trade={data.bestTrade} tone="good" ethUsd={data.ethUsd} />
          <TradeSide trade={data.worstTrade} tone="bad" ethUsd={data.ethUsd} />
        </div>
      </section>

      {data.biggestFumble ? (
        <section className="section">
          <div className="section-title">
            <h2>THE FUMBLE</h2>
            <p>Missed upside against today&apos;s floor. Painful, but not a realised loss.</p>
          </div>
          <div className="fumble-feature">
            <div className="fumble-art">
              <Mascot mood="laughing" />
            </div>
            <div className="fumble-copy">
              <div className="kicker">YOU SOLD IT FOR {formatEth(data.biggestFumble.soldEth)} ETH</div>
              <h3>{data.biggestFumble.name}</h3>
              <div className="fumble-amount">+{formatEth(data.biggestFumble.missedEth)} ETH</div>
              <p className="fumble-method">
                {data.biggestFumble.collection} floor is {formatEth(data.biggestFumble.floorEth)} ETH today.
                That is what the same NFT would fetch now, against the {formatEth(data.biggestFumble.soldEth)}{" "}
                ETH you took for it. Hypothetical missed upside — not money lost.
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {data.topCollections.length > 0 ? (
        <section className="section">
          <div className="section-title">
            <h2>WHERE IT WENT</h2>
            <p>Realised P&amp;L by collection, largest impact first.</p>
          </div>
          <table className="collection-table">
            <thead>
              <tr>
                <th>COLLECTION</th>
                <th>TRADES</th>
                <th>REALISED</th>
              </tr>
            </thead>
            <tbody>
              {data.topCollections.map((row) => (
                <tr key={row.collection}>
                  <td>{row.collection}</td>
                  <td>{row.trades}</td>
                  <td className={row.pnlEth >= 0 ? "positive" : "negative"}>
                    {row.pnlEth >= 0 ? "+" : "−"}
                    {formatEth(Math.abs(row.pnlEth))} ETH
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      <section className="section">
        <div className="section-title">
          <h2>COVERAGE</h2>
          <p>What this number does and does not include.</p>
        </div>
        <ul className="coverage">
          {data.limitations.map((line) => (
            <li key={line}>{line}</li>
          ))}
          {data.periodStart ? (
            <li>
              Earliest event covered: {new Date(data.periodStart * 1000).toISOString().slice(0, 10)}.
            </li>
          ) : null}
          {data.ethUsd ? <li>USD shown at {formatUsd(data.ethUsd)} per ETH, fetched just now.</li> : null}
        </ul>
      </section>

      <Footer />
    </main>
  );
}

function MiniMetric({
  metric,
  ethUsd,
  signed = false,
}: {
  metric: Metric;
  ethUsd: number | null;
  signed?: boolean;
}) {
  const unavailable = metric.value === null;
  const usd = metric.unit === "ETH" ? usdOf(metric.value, ethUsd) : null;
  const sign = signed && metric.value !== null ? (metric.value >= 0 ? "+" : "−") : "";
  const shown = signed && metric.value !== null ? Math.abs(metric.value) : metric.value;

  return (
    <div className="mini-metric">
      <div className="metric-label">
        {metric.label}
        <span className="confidence">{metric.confidence}</span>
      </div>
      <div className={`metric-value ${unavailable ? "unavailable" : ""}`}>
        {unavailable ? (
          "NO DATA"
        ) : (
          <>
            {sign}
            {formatMetric(shown, metric.unit)}
            <span className="metric-unit">
              {metric.unit === "COUNT" ? "NFTS" : metric.unit === "%" ? "%" : metric.unit}
            </span>
          </>
        )}
      </div>
      <p className="metric-note">
        {metric.note}
        {usd !== null ? ` ≈ ${formatUsd(usd)}.` : ""}
      </p>
    </div>
  );
}

function TradeSide({
  trade,
  tone,
  ethUsd,
}: {
  trade: Autopsy["bestTrade"];
  tone: "good" | "bad";
  ethUsd: number | null;
}) {
  if (!trade) {
    return (
      <div className={`trade-card ${tone === "bad" ? "bad" : ""}`}>
        <div className="kicker">{tone === "bad" ? "WORST TRADE" : "BEST TRADE"}</div>
        <div className="empty-data" style={{ marginTop: 28 }}>
          No {tone === "bad" ? "losing" : "winning"} trade could be reconstructed from a real purchase price
          within coverage.
        </div>
      </div>
    );
  }

  const usd = usdOf(trade.pnlEth, ethUsd);

  return (
    <div className={`trade-card ${tone === "bad" ? "bad" : ""}`}>
      <div className="kicker">{tone === "bad" ? "WORST TRADE" : "BEST TRADE"}</div>
      {trade.imageUrl ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img className="trade-thumb" src={trade.imageUrl} alt="" style={{ marginTop: 22 }} />
      ) : null}
      <h3>
        {trade.pnlEth >= 0 ? "+" : "−"}
        {formatEth(Math.abs(trade.pnlEth))} ETH
      </h3>
      <div className="collection">
        {trade.name} — {trade.collection}
        {usd !== null ? ` — ${formatUsd(Math.abs(usd))}` : ""}
      </div>
      <div className="trade-numbers">
        <div className="trade-number">
          <span>BOUGHT</span>
          <strong>{trade.boughtEth === null ? "—" : formatEth(trade.boughtEth)}</strong>
        </div>
        <div className="trade-number">
          <span>SOLD</span>
          <strong>{formatEth(trade.soldEth)}</strong>
        </div>
        <div className="trade-number">
          <span>{trade.pnlPct === null ? "HELD" : "RETURN"}</span>
          <strong>
            {trade.pnlPct === null
              ? trade.heldDays === null
                ? "—"
                : `${trade.heldDays}D`
              : `${trade.pnlPct > 0 ? "+" : ""}${trade.pnlPct}%`}
          </strong>
        </div>
      </div>
    </div>
  );
}
