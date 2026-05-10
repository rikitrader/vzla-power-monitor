"""Aggregate all sources into a single JSON snapshot.

Each source is called in isolation; failures don't propagate. The output
shape is stable so the frontend can render gracefully when any source is
down (just show "fuente desactualizada").
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sources import foro_penal, gdelt, prediction_markets, vdem  # noqa: E402

Source = tuple[str, Callable[[], dict[str, Any]]]

SOURCES: list[Source] = [
    ("vdem", vdem.fetch),
    ("gdelt", gdelt.fetch),
    ("foroPenal", foro_penal.fetch),
    ("predictionMarkets", prediction_markets.fetch),
]


def run() -> dict[str, Any]:
    snapshot_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: dict[str, Any] = {
        "snapshotAt": snapshot_at,
        "schemaVersion": 1,
        "sources": {},
    }
    summary: list[str] = []
    for key, fn in SOURCES:
        start = time.perf_counter()
        try:
            data = fn()
            elapsed = time.perf_counter() - start
            ok = bool(data.get("ok"))
            data["_ms"] = round(elapsed * 1000)
            out["sources"][key] = data
            summary.append(f"  {key:20} ok={ok!s:5} {elapsed*1000:7.0f}ms")
        except Exception as e:  # noqa: BLE001
            elapsed = time.perf_counter() - start
            out["sources"][key] = {
                "ok": False,
                "error": f"unhandled: {type(e).__name__}: {e}",
                "_ms": round(elapsed * 1000),
            }
            summary.append(f"  {key:20} ok=False {elapsed*1000:7.0f}ms ERR")
    sys.stderr.write("[aggregate] sources:\n" + "\n".join(summary) + "\n")
    return out


def main() -> int:
    snapshot = run()
    data_dir = ROOT / "data" / "snapshots"
    data_dir.mkdir(parents=True, exist_ok=True)

    latest = data_dir.parent / "latest.json"
    latest.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    archived = data_dir / f"{stamp}.json"
    archived.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")

    sys.stderr.write(f"[aggregate] wrote {latest} and {archived}\n")
    ok_count = sum(1 for s in snapshot["sources"].values() if s.get("ok"))
    sys.stderr.write(
        f"[aggregate] {ok_count}/{len(snapshot['sources'])} sources ok\n"
    )
    return 0 if ok_count > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
