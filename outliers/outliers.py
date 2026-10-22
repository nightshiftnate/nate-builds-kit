"""Outlier reel finder for Instagram. Pull a watchlist, score reels, store a local JSON file, search it.

Usage:
  python3 outliers/outliers.py pull              fetch every creator in creators.txt and rewrite the feed
  python3 outliers/outliers.py search "claude code" [--days 30] [--limit 10] [--creator handle] [--sort score|views|recent]
  python3 outliers/outliers.py hooks [--limit 10]
  python3 outliers/outliers.py recap handle
  python3 outliers/outliers.py add handle [handle ...]

Credentials come from the environment only: IG_USER_ID and IG_ACCESS_TOKEN.
Standard library only, Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- scoring rules --------------------------------------------------------
LOOKBACK_DAYS = 30
LONG_DAYS = 90       # hot-streak fallback window
MIN_SCORE = 3.0      # a hit is views / creator median >= this ...
MIN_VIEWS = 50_000   # ... and at least this many views
MIN_REELS = 5        # creator needs this many reels in the 30 days
PAID_RATIO = 150     # views per like above this (or 3x the creator's usual) looks paid
PAID_MULT = 3
PAID_ALWAYS = 1000

# ---- Graph API ------------------------------------------------------------
GRAPH = "https://graph.facebook.com/"  # unversioned = your app's default version
MEDIA_FIELDS = ("id,caption,comments_count,like_count,view_count,media_type,media_product_type,"
                "permalink,timestamp")
PROFILE_FIELDS = "username,name,followers_count,media_count"
STOP_PCT = 80  # stop cleanly when Meta reports this much of the hourly budget used
RATE_LIMIT_CODES = {4, 17, 32, 613, 80002}


def data_dir() -> Path:
    return Path(os.environ.get("OUTLIERS_HOME") or Path.home() / ".outliers")


def feed_path() -> Path:
    return data_dir() / "feed.json"


def watchlist_path() -> Path:
    return Path(os.environ.get("OUTLIERS_CREATORS") or HERE / "creators.txt")


# ---- scoring (pure functions) ----------------------------------------------
def _ts(s: str) -> datetime:
    # Meta sends +0000 with no colon; fromisoformat on 3.9 needs the strptime form.
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def _key(caption: str) -> str:
    return re.sub(r"\W+", " ", caption.lower()).strip()[:120]


def dedupe(reels):
    """Same caption posted more than once counts once, at its best view count. Empty captions never merge."""
    best = {}
    for m in reels:
        k = _key(m.get("caption") or "") or m["id"]
        if k not in best or m["view_count"] > best[k]["view_count"]:
            best[k] = m
    return list(best.values())


def usual_views_per_like(reels):
    """Median views per like over reels that show likes. None under MIN_REELS of them (likes hidden).
    Reels already over PAID_ALWAYS are left out so a creator who boosts a lot can't raise their own bar."""
    r = [m["view_count"] / m["like_count"] for m in reels
         if (m.get("like_count") or 0) > 0 and m["view_count"] / m["like_count"] <= PAID_ALWAYS]
    return round(statistics.median(r), 1) if len(r) >= MIN_REELS else None


def is_boosted(views, likes, usual):
    """Likely paid. Meta's like_count leaves out likes on promoted copies, so a paid reel has lots of views per like."""
    if not likes or not views:
        return False
    r = views / likes
    if r > PAID_ALWAYS:
        return True
    return r > (max(PAID_RATIO, PAID_MULT * usual) if usual else PAID_RATIO)


def score_creator(media, now=None):
    """Return {reels_30d, median, outliers}. Each outlier is the reel dict plus score, median, baseline_days, boosted."""
    now = now or datetime.now(timezone.utc)
    cutoff, long_cutoff = now - timedelta(days=LOOKBACK_DAYS), now - timedelta(days=LONG_DAYS)
    long = [m for m in media if m.get("media_product_type") == "REELS" and _ts(m["timestamp"]) >= long_cutoff
            and isinstance(m.get("view_count"), int) and m["view_count"] > 0]  # 0-view reels are noise
    reels = dedupe([m for m in long if _ts(m["timestamp"]) >= cutoff])
    long = dedupe(long)
    if len(reels) < MIN_REELS:
        return {"reels_30d": len(reels), "median": None, "outliers": []}
    med = statistics.median(m["view_count"] for m in reels)
    med90 = statistics.median(m["view_count"] for m in long)
    usual = usual_views_per_like(long)
    out = []
    for m in reels:
        if m["view_count"] < MIN_VIEWS:
            continue
        # The 30-day rule decides first. The 90-day rule only adds hits for creators on a streak,
        # where the 30-day median is itself inflated by hits.
        for base, days in ((med, LOOKBACK_DAYS), (med90, LONG_DAYS)):
            if m["view_count"] / base >= MIN_SCORE:
                out.append({**m, "score": round(m["view_count"] / base, 1), "median": base, "baseline_days": days,
                            "boosted": is_boosted(m["view_count"], m.get("like_count"), usual)})
                break
    out.sort(key=lambda m: -m["score"])
    return {"reels_30d": len(reels), "median": med, "outliers": out}


# ---- Graph API client -------------------------------------------------------
class RateLimited(Exception):
    pass


class Graph:
    def __init__(self, ig_id, token, max_calls=180):
        self.ig_id, self.token, self.max_calls = ig_id, token, max_calls
        self.calls = 0
        self.usage_pct = 0

    def _get(self, fields):
        if self.calls >= self.max_calls:
            raise RateLimited("run budget of %d Graph calls used" % self.max_calls)
        url = GRAPH + self.ig_id + "?" + urllib.parse.urlencode({"fields": fields, "access_token": self.token})
        self.calls += 1
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=40) as r:
                    self._read_usage(r.headers)
                    return r.status, json.load(r)
            except urllib.error.HTTPError as e:
                self._read_usage(e.headers)
                try:
                    body = json.load(e)
                except Exception:
                    body = {"error": {"message": "HTTP %d" % e.code}}
                if body.get("error", {}).get("code") in RATE_LIMIT_CODES:
                    raise RateLimited(body["error"].get("message", "rate limited"))
                if e.code >= 500 and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                return e.code, body
            except (urllib.error.URLError, TimeoutError):
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                return 599, {"error": {"message": "network error"}}
        return 599, {"error": {"message": "unreachable"}}

    def _read_usage(self, headers):
        pcts = []
        try:
            app = json.loads(headers.get("x-app-usage") or "{}")
            pcts += [v for v in app.values() if isinstance(v, (int, float))]
            buc = json.loads(headers.get("x-business-use-case-usage") or "{}")
            for rows in buc.values():
                for row in rows:
                    pcts += [row.get(k, 0) for k in ("call_count", "total_time", "total_cputime")]
        except (ValueError, AttributeError, TypeError):
            return
        self.usage_pct = max(pcts, default=0)
        if self.usage_pct >= STOP_PCT:
            raise RateLimited("Meta usage at %s%% of the hourly budget" % self.usage_pct)

    def creator(self, username, lookback_days=LONG_DAYS, max_pages=4):
        """Profile plus posts back to the lookback. Returns {'error': ...} for accounts that can't be read."""
        base = "business_discovery.username(%s){%s,media.limit(50){%s}}" % (username, PROFILE_FIELDS, MEDIA_FIELDS)
        code, body = self._get(base)
        if code != 200:
            err = body.get("error", {})
            return {"error": ("%s %s" % (err.get("code", code), err.get("message", ""))).strip()}
        bd = body["business_discovery"]
        media = bd.get("media", {})
        data = list(media.get("data", []))
        page_len = len(data)
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        for _ in range(max_pages):
            after = media.get("paging", {}).get("cursors", {}).get("after")
            if not after or not page_len or _ts(data[-1]["timestamp"]) < cutoff:
                break
            c, more = self._get(base.replace("media.limit(50)", "media.limit(50).after(%s)" % after))
            if c != 200:
                break  # keep what we have
            media = more["business_discovery"].get("media", {})
            page = media.get("data", [])
            page_len = len(page)
            data.extend(page)
        out = {k: bd.get(k) for k in PROFILE_FIELDS.split(",")}
        out["media"] = data
        return out


# ---- store ------------------------------------------------------------------
def load_feed(path=None):
    p = path or feed_path()
    if not p.exists():
        return {"generated_at": None, "creators": [], "videos": []}
    return json.loads(p.read_text())


def save_feed(feed, path=None):
    p = path or feed_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(feed, indent=1, ensure_ascii=False))
    tmp.replace(p)


def clean_handle(h):
    h = (h or "").strip().lstrip("@").lower()
    return h if h and re.fullmatch(r"[a-z0-9_.]{1,30}", h) else ""


def read_watchlist(path=None):
    p = path or watchlist_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        h = clean_handle(line.split("#")[0])
        if h and h not in out:
            out.append(h)
    return out


def video_row(o, username):
    code = (o.get("permalink") or "").rstrip("/").split("/")[-1]
    views = o["view_count"]
    return {"id": o["id"], "creator": username, "url": o.get("permalink"), "caption": o.get("caption") or "",
            "views": views, "likes": o.get("like_count"), "comments": o.get("comments_count"),
            "posted_at": o["timestamp"], "outlier_score": o["score"], "creator_median_views": o["median"],
            "baseline_days": o["baseline_days"], "boosted": o["boosted"], "code": code}


def merge_creator(feed, username, profile, scored):
    """Replace a creator's row and add their new hits. Older hits stay in the library even after they leave the
    30-day window, as long as the creator is still on the watchlist. A reel returned again gets fresh numbers."""
    new = {v["id"]: v for v in (video_row(o, username) for o in scored["outliers"])}
    keep = [v for v in feed["videos"] if v["creator"] != username or v["id"] not in new]
    feed["videos"] = keep + list(new.values())
    row = {"username": username, "name": profile.get("name"), "followers": profile.get("followers_count"),
           "median": scored["median"], "reels_30d": scored["reels_30d"],
           "outliers": sum(1 for v in feed["videos"] if v["creator"] == username)}
    feed["creators"] = [c for c in feed["creators"] if c["username"] != username] + [row]


def pull(graph, handles, path=None, log=print):
    feed = load_feed(path)
    feed["videos"] = [v for v in feed["videos"] if v["creator"] in handles]
    feed["creators"] = [c for c in feed["creators"] if c["username"] in handles]
    done = 0
    try:
        for h in handles:
            if h.startswith("example"):
                log("skipping placeholder @%s (edit creators.txt)" % h)
                continue
            prof = graph.creator(h)
            if "error" in prof:
                log("@%s: not readable (%s)" % (h, prof["error"]))
                continue
            scored = score_creator(prof["media"])
            merge_creator(feed, h, prof, scored)
            done += 1
            if scored["median"] is None:
                log("@%s: only %d reels in 30 days, need %d" % (h, scored["reels_30d"], MIN_REELS))
            else:
                log("@%s: median %d views, %d hits" % (h, scored["median"], len(scored["outliers"])))
    except RateLimited as e:
        log("stopped early: %s. Run pull again later; creators already done are saved." % e)
    feed["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    save_feed(feed, path)
    log("%d creators read, %d Graph calls, Meta usage %s%%" % (done, graph.calls, graph.usage_pct))
    return feed


# ---- queries (used by the CLI and the MCP server) ---------------------------
def brief(v):
    out = {k: v.get(k) for k in ("creator", "url", "views", "outlier_score", "creator_median_views",
                                 "baseline_days", "posted_at", "boosted")}
    out["caption"] = (v.get("caption") or "")[:160]
    return out


def first_line(caption):
    for line in (caption or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def search(feed, query="", min_score=MIN_SCORE, min_views=0, days=30, creator="", include_boosted=False,
           sort="score", limit=10, now=None):
    since = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    words = query.lower().split()
    c = clean_handle(creator)
    hits = []
    for v in feed["videos"]:
        if v["outlier_score"] < min_score or (v["views"] or 0) < min_views:
            continue
        if v["boosted"] and not include_boosted:
            continue
        if _ts(v["posted_at"]) < since or (c and v["creator"] != c):
            continue
        text = ("%s %s" % (v.get("caption") or "", v["creator"])).lower()
        if all(w in text for w in words):
            hits.append(v)
    keys = {"views": lambda v: -(v["views"] or 0), "recent": lambda v: v["posted_at"]}
    hits.sort(key=keys.get(sort, lambda v: -v["outlier_score"]), reverse=sort == "recent")
    return {"total": len(hits), "feed_updated": feed.get("generated_at"), "videos": [brief(v) for v in hits[:limit]]}


def top_hooks(feed, limit=10):
    vids = sorted((v for v in feed["videos"] if not v["boosted"]), key=lambda v: -v["outlier_score"])
    return {"feed_updated": feed.get("generated_at"),
            "note": "Caption first lines of the top hits. Label the hook format yourself.",
            "hooks": [{"hook": first_line(v.get("caption")), "creator": v["creator"], "views": v["views"],
                       "outlier_score": v["outlier_score"], "url": v["url"]} for v in vids[:limit]]}


def channel_recap(feed, creator):
    u = clean_handle(creator)
    c = next((c for c in feed["creators"] if c["username"] == u), None)
    if not c:
        return {"error": "@%s is not in the feed. Use add_channel, then run pull." % u}
    mine = [v for v in feed["videos"] if v["creator"] == u]
    return {**c, "outlier_videos": [brief(v) for v in mine if not v["boosted"]],
            "hidden_boosted": sum(1 for v in mine if v["boosted"])}


def add_channel(username, path=None):
    u = clean_handle(username)
    if not u:
        return {"error": "not an Instagram handle: %r" % username}
    p = path or watchlist_path()
    if u in read_watchlist(p):
        return {"ok": True, "note": "@%s is already on the watchlist" % u}
    text = p.read_text() if p.exists() else ""
    with p.open("a") as fh:
        fh.write(("" if not text or text.endswith("\n") else "\n") + u + "\n")
    return {"ok": True, "note": "@%s added. It is scored the next time you run pull." % u}


# ---- CLI --------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Instagram outlier reel finder")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull", help="fetch the watchlist and rewrite the feed").add_argument("--max-calls", type=int, default=180)
    s = sub.add_parser("search", help="search stored outliers")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--creator", default="")
    s.add_argument("--min-score", type=float, default=MIN_SCORE)
    s.add_argument("--sort", choices=["score", "views", "recent"], default="score")
    s.add_argument("--include-boosted", action="store_true")
    h = sub.add_parser("hooks", help="first caption line of the top hits")
    h.add_argument("--limit", type=int, default=10)
    sub.add_parser("recap", help="one creator").add_argument("creator")
    sub.add_parser("add", help="add handles to creators.txt").add_argument("handles", nargs="+")
    a = ap.parse_args(argv)

    if a.cmd == "pull":
        ig, tok = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
        if not (ig and tok):
            sys.exit("Set IG_USER_ID and IG_ACCESS_TOKEN first. See the README.")
        handles = read_watchlist()
        if not handles:
            sys.exit("No handles in %s" % watchlist_path())
        pull(Graph(ig, tok, max_calls=a.max_calls), handles)
        return
    feed = load_feed()
    if a.cmd == "search":
        res = search(feed, a.query, a.min_score, 0, a.days, a.creator, a.include_boosted, a.sort, a.limit)
    elif a.cmd == "hooks":
        res = top_hooks(feed, a.limit)
    elif a.cmd == "recap":
        res = channel_recap(feed, a.creator)
    else:
        res = [add_channel(x) for x in a.handles]
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
