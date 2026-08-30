import { cache } from "react";
import { buildAutopsy } from "./engine";
import { buildShareText } from "./format";
import { Upstream, openseaKey } from "./opensea";
import { ethUsdRate } from "./price";
import type { Autopsy } from "./types";

export type LoadResult =
  | { ok: true; data: Autopsy }
  | { ok: false; reason: "NOT_CONFIGURED" | "FAILED" };

/**
 * Single entry point for the page, its metadata and its OG image. `cache`
 * dedupes the work within one render pass.
 */
export const loadAutopsy = cache(async (address: string): Promise<LoadResult> => {
  const key = openseaKey();
  if (!key) return { ok: false, reason: "NOT_CONFIGURED" };

  try {
    const up = new Upstream(key);
    const ethUsd = await ethUsdRate();
    const data = await buildAutopsy(up, address.toLowerCase(), { ethUsd });
    data.shareLine = buildShareText(data);
    return { ok: true, data };
  } catch (error) {
    console.error("loadAutopsy failed", error);
    return { ok: false, reason: "FAILED" };
  }
});
