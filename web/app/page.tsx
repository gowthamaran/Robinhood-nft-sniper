import Link from "next/link";
import { Footer, Topbar } from "@/components/Chrome";
import { Mascot } from "@/components/Mascot";
import { WalletSearch } from "@/components/WalletSearch";

const TICKER =
  "REALIZED PNL ◆ WIN RATE ◆ BEST TRADE ◆ WORST TRADE ◆ MISSED UPSIDE ≠ LOSS ◆ NO SEED PHRASE ◆ NO SIGNATURE ◆ ";

export default function HomePage() {
  return (
    <main className="site-shell">
      <Topbar />

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="live-dot" /> NFT WALLET AUTOPSY / READ-ONLY
          </div>
          <h1>
            HOW MUCH DID YOU <span className="slash">FUMBLE?</span>
          </h1>
          <p className="subhead">
            Paste a wallet. We pair every buy with every sale and tell you exactly what you made, what you
            lost, and what you left on the table.
          </p>
          <WalletSearch />
          <Link className="demo-link" href="/wallet/0xd8da6bf26964af9d7eed9e03e53415d37aa96045">
            or autopsy vitalik.eth first →
          </Link>
          <p className="privacy-note">
            No wallet connection. No signing. Just public onchain embarrassment.
          </p>
        </div>

        <div className="hero-visual">
          <div className="ticker" aria-hidden="true">
            <span>
              {TICKER}
              {TICKER}
            </span>
          </div>
          <div className="mascot-stage">
            <Mascot mood="laughing" />
            <div className="mascot-caption">HE SAW YOUR SELL HISTORY.</div>
          </div>
        </div>
      </section>

      <section className="proof-strip" aria-label="Product facts">
        <div className="proof-item">
          <strong>0 KEYS</strong>
          <span>WE WILL NEVER ASK</span>
        </div>
        <div className="proof-item">
          <strong>PUBLIC</strong>
          <span>ONCHAIN DATA ONLY</span>
        </div>
        <div className="proof-item">
          <strong>FIFO</strong>
          <span>NO FAKE COST BASIS</span>
        </div>
        <div className="proof-item">
          <strong>PAINFUL</strong>
          <span>SCREENSHOT READY</span>
        </div>
      </section>

      <section className="manifesto">
        <div>
          <div className="kicker">THE MONEY DESK</div>
          <h2>THREE NUMBERS. VERY DIFFERENT PAIN.</h2>
        </div>
        <div className="manifesto-copy">
          <article className="manifesto-card">
            <b>01 / REALIZED</b>
            <h3>MADE &amp; LOST</h3>
            <p>
              Every sale paired against the buy that funded it, FIFO. Winners and losers are counted
              separately, so a good year cannot hide a bad one.
            </p>
          </article>
          <article className="manifesto-card">
            <b>02 / OPEN</b>
            <h3>HOLDING</h3>
            <p>
              What is still in the wallet right now. Counted, never valued with a number we cannot defend.
            </p>
          </article>
          <article className="manifesto-card">
            <b>03 / HYPOTHETICAL</b>
            <h3>FUMBLED</h3>
            <p>
              What today&apos;s floor would pay for the things you already sold. Emotionally devastating.
              Financially not a loss.
            </p>
          </article>
        </div>
      </section>

      <Footer />
    </main>
  );
}
