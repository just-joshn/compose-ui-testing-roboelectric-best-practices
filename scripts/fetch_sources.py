#!/usr/bin/env python3
"""Fetch the current text of every official page the skill cites into .cache/sources/.

Release notes are cut to current releases: the latest Robolectric release and the current
stable and newer Compose UI lines.

Usage: fetch_sources.py [URL ...]   (no arguments: every URL cited by the skill or its ledgers)
"""
import html
import json
import re
import sys
import urllib.request

from official import CACHE, cache_file, canonical, cited_urls, is_allowed, rendered_file

LATEST_RELEASE_API = "https://api.github.com/repos/robolectric/robolectric/releases/latest"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "skill-source-check"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|pre|table|dt|dd)>", "\n", raw)
    return html.unescape(re.sub(r"<[^>]+>", "", raw))


def article_text(raw):
    """The rendered article, so link text that the markdown export drops is kept."""
    m = re.search(r"(?is)<article\b.*?</article>", raw)
    return html_to_text(m.group(0) if m else raw)


def current_release_notes(text):
    """Keep the version table and the notes for the current stable and newer lines only."""
    stable = re.search(r"\|\s*\w+ \d+, \d{4}\s*\|\s*\[?(\d+\.\d+)\.\d+", text).group(1)
    start = text.index(f"\n## Version {stable}\n")
    nxt = text.find("\n## Version ", start + 1)
    return text if nxt < 0 else text[:nxt]


def fetch(url):
    if url.startswith("https://github.com/robolectric/robolectric/releases"):
        r = json.loads(get(LATEST_RELEASE_API))
        return f"# {r['name'] or r['tag_name']} ({r['published_at']})\n{r['body'] or ''}"
    if url.startswith("https://developer.android.com/jetpack/androidx/releases/"):
        return current_release_notes(get(url + ".md.txt"))
    if url.startswith("https://developer.android.com/"):
        return get(url + ".md.txt")
    return html_to_text(get(url))


def main(argv):
    urls = sorted({canonical(u) for u in argv} or cited_urls())
    CACHE.mkdir(parents=True, exist_ok=True)
    failed = []
    for url in urls:
        if not is_allowed(url):
            failed.append(f"not an official source: {url}")
            continue
        try:
            cache_file(url).write_text(fetch(url))
            if url.startswith("https://developer.android.com/"):
                rendered_file(url).write_text(article_text(get(url)))
        except Exception as exc:  # report every failed page, then exit non-zero
            failed.append(f"{url}: {exc}")
    for line in failed:
        print(line)
    print(f"fetched {len(urls) - len(failed)}/{len(urls)} pages")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
