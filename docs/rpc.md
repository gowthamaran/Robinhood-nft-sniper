# RPC selection

Use a reputable Robinhood Chain provider. Configure one primary and up to five explicit backups. The public Robinhood endpoint is useful for setup and fallback but may be rate-limited. The project never invents, scrapes or races arbitrary endpoints.

Run repeated benchmarks near the mint time. Prefer consistent freshness and reliability over a single lowest ping. Authenticated provider URLs are credentials: config is local mode `600`, and output/log redaction hides common URL formats, but unusual provider schemes may require an additional sanitizer rule.

Submission uses the same signed bytes on at most two endpoints. This improves propagation robustness without nonce races, competing transactions or replacement spam.
