"""Prediction markets — pulls the live snapshot from tuvzla.com.

The /api/markets endpoint on the venezuela-primero CF Pages site already
hits Polymarket + Manifold and edge-caches for 5 minutes. We mirror the
snapshot into the power-monitor JSON so the dashboard has everything in
one payload.
"""

from __future__ import annotations

from typing import Any

import requests

URL = "https://tuvzla.com/api/markets"
TIMEOUT = 20


def fetch() -> dict[str, Any]:
    try:
        r = requests.get(
            URL, timeout=TIMEOUT, headers={"User-Agent": "vzla-power-monitor/1.0"}
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "source": "tuvzla.com /api/markets (Polymarket + Manifold)",
            "url": URL,
            "error": f"fetch failed: {e}",
        }

    return {
        "ok": True,
        "source": "Polymarket Gamma + Manifold Markets",
        "url": URL,
        "fetchedAt": data.get("fetchedAt"),
        "sources": data.get("sources", {}),
        "markets": data.get("markets", []),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(fetch(), indent=2, ensure_ascii=False))
