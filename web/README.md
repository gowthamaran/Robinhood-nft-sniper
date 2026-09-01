# fumbled.lol

The web app behind [fumbled-lol.vercel.app](https://fumbled-lol.vercel.app) — a read-only NFT wallet
autopsy. Paste an Ethereum address and it reconstructs what the wallet actually made and lost on NFTs.

## What it computes

Every figure is rebuilt from public OpenSea-indexed Ethereum activity. Sales are paired against the
purchases that funded them, oldest lot first (FIFO), per token:

| Figure | Meaning |
| --- | --- |
| `MADE` | Sum of every winning FIFO-matched trade |
| `LOST` | Magnitude of every losing FIFO-matched trade |
| `NET` | Made minus lost, gross of gas and marketplace fees |
| `FUMBLED` | `Σ max(today's collection floor − your sale price, 0)` — hypothetical missed upside |
| `FLIPPING` | Realised P&L on trades closed within 7 days |
| `MINT TAKE` | Proceeds from minted NFTs later sold (mint cost and gas excluded) |
| `WIN RATE` | Winning trades over all FIFO-matched trades |
| `NFT IQ` | `clamp(0, 100, 0.60 × profitability + 0.40 × win rate)`, deterministic |

An NFT acquired by mint, airdrop or transfer has no on-chain purchase price, so it never receives an
invented zero cost basis — the sale records proceeds but contributes no P&L. Sales in currencies we
cannot convert without guessing a historical rate are skipped rather than estimated.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENSEA_API_KEY` | yes | Reads account events, holdings and collection floors |
| `NEXT_PUBLIC_SITE_ORIGIN` | no | Canonical origin for share links and OG images; defaults to the Vercel production URL |

Without `OPENSEA_API_KEY` the app returns a clearly worded 503 rather than fabricated numbers.

## Development

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # ledger and scoring unit tests
npm run typecheck
npm run build
```

## Sharing

Each `/wallet/<address>` page renders an OG image at `/wallet/<address>/opengraph-image` containing the
wallet's real numbers, so pasting the link into X unfurls a card with the result on it. The share rail
also opens a pre-filled X post and copies the link.
