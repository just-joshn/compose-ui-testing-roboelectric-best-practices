"""Shared definitions: the official-source boundary, the page cache, and text normalization."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "compose-ui-testing-robolectric-best-practices"
LEDGER = ROOT / "verification"
CACHE = ROOT / ".cache" / "sources"
_LINES = [l.strip() for l in (ROOT / "sources.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
PREFIXES = [l.rstrip("/") for l in _LINES if not l.startswith("!")]
EXCLUDED = [l[1:].rstrip("/") for l in _LINES if l.startswith("!")]


def canonical(url):
    return url.split("#")[0].split("?")[0].rstrip("/.,;:").rstrip("/")


def is_allowed(url):
    url = canonical(url)
    def under(prefixes):
        return any(url == p or url.startswith(p + "/") for p in prefixes)
    return under(PREFIXES) and not under(EXCLUDED)


def cache_file(url):
    return CACHE / (hashlib.sha1(canonical(url).encode()).hexdigest() + ".txt")


def rendered_file(url):
    return cache_file(url).with_suffix(".html.txt")


def page_text(url):
    path = cache_file(url)
    return path.read_text() if path.exists() else None


def page_texts(url):
    """The page as markdown source and, where saved, as rendered article text (keeps link words)."""
    return [p.read_text() for p in (cache_file(url), rendered_file(url)) if p.exists()]


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
