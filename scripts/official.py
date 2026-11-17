"""Shared definitions: the official-source boundary, the page cache, and text normalization."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "compose-ui-testing-robolectric-best-practices"
LEDGER = ROOT / "verification"
CACHE = ROOT / ".cache" / "sources"
PREFIXES = [
    line.strip().rstrip("/")
    for line in (ROOT / "sources.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]


def canonical(url):
    return url.split("#")[0].split("?")[0].rstrip("/.,;:").rstrip("/")


def is_allowed(url):
    url = canonical(url)
    return any(url == p or url.startswith(p + "/") for p in PREFIXES)


def cache_file(url):
    return CACHE / (hashlib.sha1(canonical(url).encode()).hexdigest() + ".txt")


def page_text(url):
    path = cache_file(url)
    return path.read_text() if path.exists() else None


def normalize(text):
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").replace("**", "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def cited_urls():
    urls = set()
    for md in SKILL.rglob("*.md"):
        prose = re.sub(r"(?ms)^(```|~~~).*?^\1", "", md.read_text())
        prose = re.sub(r"`[^`\n]*`", "", prose)
        urls.update(re.findall(r"https?://[^\s)>`\"']+", prose))
    for led in LEDGER.rglob("*.json"):
        for unit in json.loads(led.read_text())["units"]:
            urls.update(q["url"] for q in unit.get("quotes", []))
    return {canonical(u) for u in urls}
