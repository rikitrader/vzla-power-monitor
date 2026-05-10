"""Foro Penal — count of political prisoners in Venezuela.

Scraped from foropenal.com homepage. They publish a weekly summary post
("Balance de #PresosPoliticos") and the headline counts also appear in the
homepage og:description meta tag. We parse both as fallbacks.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import requests

URL = "https://foropenal.com/"
TIMEOUT = 20

# Pattern e.g. "Total presos políticos: 457" (with optional bold-unicode chars).
_TOTAL_RE = re.compile(
    r"(?:total|𝗧𝗼𝘁𝗮𝗹)\s+(?:presos|𝗽𝗿𝗲𝘀𝗼𝘀)\s+(?:pol[íi]ticos|𝗽𝗼𝗹[íi]𝘁𝗶𝗰𝗼𝘀)\s*:?\s*(\d{2,5})",
    re.IGNORECASE,
)
# Two distinct formats appear on the homepage:
#  1. Weekly-balance post body:  "Civiles: 270" / "Hombres: 414"
#  2. Hero meta description:     "187 Militares  43 Mujeres  1 Adolescente"
# Parse format 1 first (more authoritative); fall back to 2.
_CATEGORY_PREFIXED_RE = re.compile(
    r"(?P<cat>Hombres|Mujeres|Civiles|Militares|Adolescentes|Adolescente|Extranjeros|Periodistas)\s*:\s*(\d{1,5})",
    re.IGNORECASE,
)
_CATEGORY_SUFFIXED_RE = re.compile(
    r"(\d{1,5})\s+(?P<cat>Militares|Civiles|Hombres|Mujeres|Adolescentes|Adolescente|Extranjeros|Periodistas)\b",
)
# Date pattern in og:description e.g. "4 de mayo 2026" or "04/05/2026"
_DATE_LONG_RE = re.compile(
    r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})",
    re.IGNORECASE,
)
_DATE_NUMERIC_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}


def _strip_tags(html: str) -> str:
    """Drop tags but keep spacing, so adjacent words don't collide."""
    return re.sub(r"<[^>]+>", " ", html)


def fetch() -> dict[str, Any]:
    """Return:
        {
            "ok": bool,
            "asOf": "YYYY-MM-DD" | None,
            "total": int | None,
            "categories": {"Militares": 187, "Civiles": 270, ...},
            "url": URL,
        }
    """
    try:
        r = requests.get(
            URL,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 vzla-power-monitor/1.0"},
        )
        r.raise_for_status()
        html = r.text
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "source": "Foro Penal",
            "url": URL,
            "error": f"fetch failed: {e}",
        }

    text = _strip_tags(html)
    text = re.sub(r"\s+", " ", text)

    # Total: try the weekly post pattern first, then any 3-4 digit number
    # immediately before "PRESOS POLITICOS" in the og:description.
    total: int | None = None
    m = _TOTAL_RE.search(text)
    if m:
        total = int(m.group(1))

    # Canonical category labels.
    cat_map = {
        "Militares": "Militares",
        "Civiles": "Civiles",
        "Hombres": "Hombres",
        "Mujeres": "Mujeres",
        "Adolescentes": "Adolescentes",
        "Adolescente": "Adolescentes",
        "Extranjeros": "Extranjeros",
        "Periodistas": "Periodistas",
    }

    categories: dict[str, int] = {}

    # Pass 1: prefixed format from the weekly balance post body.
    #   "Hombres: 414  Mujeres: 43  Civiles: 270  Militares: 187"
    for m in _CATEGORY_PREFIXED_RE.finditer(text):
        canon = cat_map.get(m.group("cat").title(), m.group("cat").title())
        try:
            n = int(m.group(2))
        except ValueError:
            continue
        # First win — homepage post is at the top.
        categories.setdefault(canon, n)

    # Pass 2: suffixed format from the meta description, for any categories
    # the prefixed pass didn't catch (e.g. when the homepage hero shows a
    # category that isn't in this week's balance text).
    for m in _CATEGORY_SUFFIXED_RE.finditer(text):
        canon = cat_map.get(m.group("cat"), m.group("cat"))
        if canon in categories:
            continue
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        categories[canon] = n

    # If we found Hombres+Mujeres but not total, sum them.
    if total is None and "Hombres" in categories and "Mujeres" in categories:
        total = categories["Hombres"] + categories["Mujeres"]

    # As-of date
    as_of: str | None = None
    m = _DATE_NUMERIC_RE.search(text)
    if m:
        d, mo, y = m.groups()
        try:
            as_of = f"{y}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            pass
    if not as_of:
        m = _DATE_LONG_RE.search(text)
        if m:
            d, mo_name, y = m.groups()
            mo = _MONTHS.get(mo_name.lower())
            if mo:
                as_of = f"{y}-{mo:02d}-{int(d):02d}"

    return {
        "ok": total is not None or bool(categories),
        "source": "Foro Penal",
        "url": URL,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asOf": as_of,
        "total": total,
        "categories": categories,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(fetch(), indent=2, ensure_ascii=False))
