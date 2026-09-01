import { NextRequest } from "next/server";
import { buildAutopsy } from "@/lib/engine";
import { buildShareText, isAddress } from "@/lib/format";
import { Upstream, openseaKey } from "@/lib/opensea";
import { ethUsdRate } from "@/lib/price";

export const runtime = "nodejs";
export const maxDuration = 60;
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, ctx: { params: Promise<{ address: string }> }) {
  const { address: raw } = await ctx.params;
  const address = (raw ?? "").trim();

  if (!isAddress(address)) {
    return Response.json({ error: "INVALID_ADDRESS" }, { status: 400 });
  }

  const key = openseaKey();
  if (!key) {
    return Response.json(
      {
        error: "NOT_CONFIGURED",
        message: "OPENSEA_API_KEY is not set for this deployment, so no live data can be read.",
      },
      { status: 503 },
    );
  }

  const up = new Upstream(key);
  const ethUsd = await ethUsdRate();

  try {
    const data = await buildAutopsy(up, address.toLowerCase(), { ethUsd });

    if (!up.reachable) {
      return Response.json(
        { error: "UPSTREAM_UNREACHABLE", message: "OpenSea did not answer, so there is nothing to report." },
        { status: 502 },
      );
    }

    data.shareLine = buildShareText(data);

    const payload: Record<string, unknown> = { ...data };
    // Upstream call trace is available off production only, for verification.
    if (req.nextUrl.searchParams.get("diag") === "1" && process.env.VERCEL_ENV !== "production") {
      payload._upstream = { calls: up.calls, rateLimited: up.rateLimited };
    }

    return Response.json(payload, {
      headers: {
        "Cache-Control": "public, s-maxage=300, stale-while-revalidate=1800",
      },
    });
  } catch (error) {
    console.error("autopsy failed", error);
    return Response.json({ error: "UPSTREAM_FAILED" }, { status: 502 });
  }
}
