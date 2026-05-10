"""GDELT — daily count of news articles mentioning Venezuela.

Public API at api.gdeltproject.org, no auth, but rate-limited to 1
request per 5 seconds per IP. Times out gracefully.
"""

from __future__ import annotations

import time
from typing import Any

import requests

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
TIMEOUT = 25


def _fetch_timeline(query: str, timespan: str = "90d") -> dict[str, Any]:
    """Return GDELT timeline volume for a query."""
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "timespan": timespan,
    }
    r = requests.get(
        BASE,
        params=params,
        timeout=TIMEOUT,
        headers={"User-Agent": "vzla-power-monitor/1.0"},
    )
    r.raise_for_status()
    return r.json()


def _normalize_timeline(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten GDELT timeline payload to [{date: YYYY-MM-DD, value: N}].

    Raw GDELT date format is YYYYMMDDT000000Z.
    """
    series = payload.get("timeline") or []
    if not series:
        return []
    data = series[0].get("data") or []
    out: list[dict[str, Any]] = []
    for pt in data:
        raw_date = str(pt.get("date", ""))
        if len(raw_date) >= 8:
            iso = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        else:
            iso = raw_date
        out.append({"date": iso, "value": int(pt.get("value", 0))})
    return out


def fetch() -> dict[str, Any]:
    """Return:
        {
            "ok": bool,
            "fetchedAt": iso,
            "timespan": "90d",
            "queries": [
                {"key": "venezuela", "label": "Venezuela", "series": [...]},
                {"key": "maduro", "label": "Maduro", "series": [...]},
                {"key": "protests", "label": "Protestas Venezuela", "series": [...]},
            ],
            "errors": [...]
        }
    """
    queries = [
        ("venezuela", "venezuela", "Cobertura general"),
        ("maduro", "venezuela maduro", "Maduro / régimen"),
        ("protests", "venezuela (protest OR protesta OR manifestación)", "Protestas"),
        ("sanctions", "venezuela (sanction OR sanción OR ofac OR chevron)", "Sanciones / OFAC"),
    ]
    out: list[dict[str, Any]] = []
    errors: list[str] = []

    for key, q, label in queries:
        try:
            payload = _fetch_timeline(q)
            series = _normalize_timeline(payload)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{key}: {e}")
            continue
        out.append({"key": key, "label": label, "query": q, "series": series})
        # GDELT rate limit: 1 req per 5 seconds.
        time.sleep(5.5)

    return {
        "ok": bool(out),
        "source": "GDELT 2.0 DOC API",
        "url": "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
        "timespan": "90d",
        "queries": out,
        "errors": errors or None,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(fetch(), indent=2, ensure_ascii=False))
