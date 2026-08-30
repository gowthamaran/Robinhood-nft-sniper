import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Fumbled.lol — how much did your NFT wallet fumble?";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#13130F",
          color: "#F1EADB",
          fontFamily: "sans-serif",
          padding: 76,
        }}
      >
        <div style={{ display: "flex", fontSize: 26, letterSpacing: 4, color: "#F1EADB99" }}>
          NFT WALLET AUTOPSY / READ-ONLY
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            fontSize: 116,
            fontWeight: 800,
            letterSpacing: -6,
            lineHeight: 1,
            marginTop: 24,
          }}
        >
          <div style={{ display: "flex" }}>HOW MUCH DID</div>
          <div style={{ display: "flex" }}>
            YOU&nbsp;<span style={{ color: "#E3432F" }}>FUMBLE?</span>
          </div>
        </div>
        <div style={{ display: "flex", fontSize: 32, color: "#F1EADB", marginTop: 30 }}>
          Paste a wallet. Get what it really made and lost on NFTs.
        </div>
        <div style={{ display: "flex", fontSize: 28, color: "#F5D90A", marginTop: 44 }}>FUMBLED.LOL</div>
      </div>
    ),
    size,
  );
}
