"""V-Dem (Varieties of Democracy) — annual democracy index for Venezuela.

Source: Our World In Data, which mirrors the V-Dem dataset (~v15) and
exposes a CSV download per indicator. OWID is more reliable than scraping
v-dem.net directly, which serves a 500MB combined dataset.

Pulls 5 core indices for Venezuela's last 25 years:
  - liberal-democracy-index
  - electoral-democracy-index
  - participatory-democracy-index
  - deliberative-democracy-index
  - egalitarian-democracy-index
"""

from __future__ import annotations

import csv
import io
import time
from typing import Any

import requests

INDICES = [
    ("liberal", "liberal-democracy-index", "Democracia liberal"),
    ("electoral", "electoral-democracy-index", "Democracia electoral"),
    ("participatory", "participatory-democracy-index", "Democracia participativa"),
    ("deliberative", "deliberative-democracy-index", "Democracia deliberativa"),
    ("egalitarian", "egalitarian-democracy-index", "Democracia igualitaria"),
]

OWID_BASE = "https://ourworldindata.org/grapher"
COUNTRY_CODE = "VEN"
SINCE_YEAR = 2000
TIMEOUT = 25


def _fetch_csv(slug: str) -> list[dict[str, str]]:
    url = f"{OWID_BASE}/{slug}.csv?country=Venezuela&v=1"
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "vzla-power-monitor/1.0"})
    r.raise_for_status()
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)


def fetch() -> dict[str, Any]:
    """Return a dict of:
        {
            "ok": bool,
            "lastYear": int,
            "scores": [{"year": 2025, "liberal": 0.05, "electoral": ..., ...}],
            "indices": [{"key": "liberal", "slug": ..., "label": ...}, ...],
        }
    """
    by_year: dict[int, dict[str, Any]] = {}
    errors: list[str] = []

    for key, slug, _label in INDICES:
        try:
            rows = _fetch_csv(slug)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{key}: {e}")
            continue

        # OWID CSV columns vary; the value column is the last non-meta column.
        # Typically: Entity, Code, Year, <indicator>, World region…
        if not rows:
            errors.append(f"{key}: empty")
            continue

        cols = list(rows[0].keys())
        try:
            value_col = next(c for c in cols if c not in {"Entity", "Code", "Year"} and c)
        except StopIteration:
            errors.append(f"{key}: no value col")
            continue

        for row in rows:
            if row.get("Code") != COUNTRY_CODE:
                continue
            try:
                year = int(row["Year"])
            except (KeyError, ValueError):
                continue
            if year < SINCE_YEAR:
                continue
            try:
                value = float(row[value_col])
            except (KeyError, ValueError, TypeError):
                continue
            by_year.setdefault(year, {"year": year})[key] = round(value, 4)

        # OWID's CSV grapher endpoint is generous but be polite.
        time.sleep(0.3)

    scores = sorted(by_year.values(), key=lambda r: r["year"])
    last_year = scores[-1]["year"] if scores else None

    return {
        "ok": bool(scores),
        "source": "V-Dem (vía Our World In Data)",
        "url": "https://ourworldindata.org/democracy",
        "lastYear": last_year,
        "scores": scores,
        "indices": [{"key": k, "slug": s, "label": l} for k, s, l in INDICES],
        "errors": errors or None,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(fetch(), indent=2, ensure_ascii=False))
