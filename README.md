# vzla-power-monitor

Python poller that snapshots Venezuela power-transformation indicators from
public sources, then commits the JSON to this repo for the tuvzla.com
dashboard to consume.

## Sources (Phase 1)

| Source | What | Cadence | Auth |
|---|---|---|---|
| **V-Dem** (via OWID) | Annual democracy indices (liberal/electoral/etc.) for Venezuela 2000–latest | annual | none |
| **GDELT 2.0 DOC** | Daily article counts mentioning Venezuela / Maduro / protests / sanctions, 90 d window | daily | none |
| **Foro Penal** | Current count of political prisoners + category breakdown, scraped weekly | weekly | none |
| **Polymarket + Manifold** | Mirror of `tuvzla.com/api/markets` | every 5 min upstream | none |

## Output

```
data/latest.json              ← always the most recent snapshot
data/snapshots/<ts>.json      ← archive
```

Shape: see `src/aggregate.py`. Stable enough that a source going down only
flips its `ok: false`; the rest of the JSON is unaffected.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.aggregate
```

Single source for debugging:

```bash
.venv/bin/python -m src.sources.foro_penal
.venv/bin/python -m src.sources.gdelt
```

## CI

`.github/workflows/poll.yml` runs every 6 h (cron `0 */6 * * *`) and on
`workflow_dispatch`. Commits `data/` back to `main` if anything changed.

## Why no database?

A flat JSON in git keeps the system reviewable (git blame on a number is
useful) and frees us from a runtime DB. Dashboard reads via Cloudflare
Pages function → GitHub raw URL with edge caching.
