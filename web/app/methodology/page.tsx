import type { Metadata } from "next";
import { Footer, Topbar } from "@/components/Chrome";

export const metadata: Metadata = {
  title: "Methodology",
  description:
    "How Fumbled.lol pairs buys with sales to calculate realised NFT profit, loss, win rate, flips and fumbled upside.",
};

export default function MethodologyPage() {
  return (
    <main>
      <Topbar />
      <article className="methodology">
        <div className="kicker">NO MYSTERY MEAT MATH</div>
        <h1>HOW THE AUTOPSY WORKS.</h1>

        <section className="method-block">
          <h2>Where the data comes from</h2>
          <div>
            <p>
              Every number is rebuilt from public Ethereum activity indexed by OpenSea: the sales, mints and
              transfers that touched the address you pasted. Nothing is read from your wallet, because your
              wallet is never connected.
            </p>
            <p>
              Trades that never touched OpenSea&apos;s index — some Blur volume and private sales — are not
              counted. A wallet that traded mostly elsewhere will look quieter here than it really was.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>Made &amp; lost</h2>
          <div>
            <p>
              Each sale is paired against the purchase that funded it, oldest lot first (FIFO), per token.
              A pairing only counts when both sides settled in ETH or WETH.
            </p>
            <div className="formula">
              TRADE P&amp;L = SALE PRICE − PURCHASE PRICE (same token, FIFO, ETH-denominated)
            </div>
            <p>
              <strong>Made</strong> is the sum of every winning trade. <strong>Lost</strong> is the magnitude
              of every losing trade. They are reported separately on purpose: a single net figure lets a good
              year hide a bad one. <strong>Net</strong> is simply made minus lost.
            </p>
            <p>
              Gas and marketplace fees are not attributed, so realised P&amp;L is gross. Your true net is
              slightly worse than what you see here.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>What is never invented</h2>
          <div>
            <p>
              An NFT that arrived by mint, airdrop or plain transfer has no purchase price on chain, so it
              never receives an invented zero cost basis. Selling it still records the proceeds, but the trade
              carries no P&amp;L and is excluded from made, lost and win rate.
            </p>
            <p>
              Sales settled in a currency we cannot convert without guessing a historical rate are skipped
              rather than estimated. Unavailable is always better than invented.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>Fumbled</h2>
          <div>
            <p>
              Fumbled is hypothetical missed upside, not a financial loss. For every NFT the wallet sold, it
              compares the sale price against what the same collection&apos;s floor would pay today.
            </p>
            <div className="formula">FUMBLED = Σ max(TODAY&apos;S COLLECTION FLOOR − YOUR SALE PRICE, 0)</div>
            <p>
              This is a present-day comparison, clearly labelled as estimated. It is not a claim about the
              historical peak, and only ETH-denominated floors are used.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>Flipping, mints &amp; win rate</h2>
          <div>
            <p>
              A <strong>flip</strong> is a trade opened and closed within seven days; the figure shown is the
              realised P&amp;L of those trades. <strong>Win rate</strong> is winning trades over all
              FIFO-matched trades. <strong>Mint take</strong> is the proceeds from NFTs this wallet minted and
              later sold — mint price and gas are not deducted, so it is a gross take, marked estimated.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>NFT IQ</h2>
          <div>
            <p>
              Deterministic, never random. It blends how much of the wallet&apos;s turnover ended up as
              profit with how often it was right, and pulls thin histories toward neutral rather than
              flattering or punishing them.
            </p>
            <div className="formula">
              SCORE = clamp(0, 100, 0.60 × PROFITABILITY + 0.40 × WIN RATE)
              <br />
              PROFITABILITY = 50 + 50 × NET ÷ (MADE + LOST)
            </div>
            <p>Fewer than three closed trades? The score is averaged halfway back to 50.</p>
          </div>
        </section>

        <section className="method-block">
          <h2>Coverage</h2>
          <div>
            <p>
              A run reads up to 1,000 recent Ethereum events and the current holdings, and every result states
              the event count and the earliest date it covers. If OpenSea rate-limits the request mid-run, the
              result says so instead of quietly returning less.
            </p>
          </div>
        </section>

        <section className="method-block">
          <h2>Privacy</h2>
          <div>
            <p>
              Fumbled.lol reads public wallet activity. It does not connect a wallet, request a signature, or
              accept a seed phrase or private key. NFT metadata is rendered as plain text and images are only
              loaded over https — never executed as HTML or SVG.
            </p>
          </div>
        </section>
      </article>
      <Footer />
    </main>
  );
}
