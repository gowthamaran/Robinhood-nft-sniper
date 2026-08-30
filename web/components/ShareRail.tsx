"use client";

import { useState } from "react";

export function ShareRail({ tweetHref, pageUrl, cardUrl }: { tweetHref: string; pageUrl: string; cardUrl: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(pageUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="share-rail">
      <a className="share-button primary" href={tweetHref} target="_blank" rel="noopener noreferrer">
        POST THIS ON X →
      </a>
      <button className="share-button secondary" type="button" onClick={copy}>
        {copied ? "LINK COPIED ✓" : "COPY LINK"}
      </button>
      <a className="share-button secondary" href={cardUrl} target="_blank" rel="noopener noreferrer">
        DOWNLOAD CARD
      </a>
      <span className="share-hint">The link unfurls on X with your numbers on it.</span>
    </div>
  );
}
