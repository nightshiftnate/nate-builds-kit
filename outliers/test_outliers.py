"""Tests for outliers.py and mcp_server.py. Run: python3 -m pytest outliers  (or python3 outliers/test_outliers.py)

All data is made up. No network, no credentials.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outliers as o  # noqa: E402
import mcp_server as mcp  # noqa: E402

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)


def reel(i, views, days_ago=5, caption=None, likes=None):
    t = NOW - timedelta(days=days_ago, minutes=i)
    return {"id": "r%d" % i, "caption": caption if caption is not None else "caption %d" % i,
            "view_count": views, "like_count": likes if likes is not None else max(views // 40, 1),
            "comments_count": 1, "media_product_type": "REELS", "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "permalink": "https://www.instagram.com/reel/CODE%d/" % i}


def base_media():
    # five ordinary reels around 10k views
    return [reel(i, 10_000 + i * 100, days_ago=i + 1) for i in range(5)]


class Scoring(unittest.TestCase):
    def test_hit_needs_3x_and_50k(self):
        m = base_media() + [reel(10, 200_000, days_ago=2)]
        s = o.score_creator(m, now=NOW)
        self.assertEqual([x["id"] for x in s["outliers"]], ["r10"])
        self.assertEqual(s["outliers"][0]["baseline_days"], 30)
        self.assertGreaterEqual(s["outliers"][0]["score"], 3)

    def test_under_50k_is_not_a_hit_even_at_high_multiple(self):
        m = base_media() + [reel(10, 49_000, days_ago=2)]
        self.assertEqual(o.score_creator(m, now=NOW)["outliers"], [])

    def test_under_3x_is_not_a_hit(self):
        m = [reel(i, 100_000, days_ago=i + 1) for i in range(5)] + [reel(10, 250_000, days_ago=2)]
        self.assertEqual(o.score_creator(m, now=NOW)["outliers"], [])

    def test_needs_five_reels(self):
        m = base_media()[:3] + [reel(10, 500_000, days_ago=2)]
        s = o.score_creator(m, now=NOW)
        self.assertEqual(s["outliers"], [])
        self.assertIsNone(s["median"])
        self.assertEqual(s["reels_30d"], 4)

    def test_zero_view_reels_and_non_reels_ignored(self):
        m = base_media() + [reel(20 + i, 0, days_ago=3) for i in range(10)]
        post = reel(30, 900_000, days_ago=1)
        post["media_product_type"] = "FEED"
        s = o.score_creator(m + [post], now=NOW)
        self.assertEqual(s["median"], 10_200)
        self.assertEqual(s["outliers"], [])

    def test_hot_streak_uses_90_day_median(self):
        # last 30 days: 3 big reels + 2 small, so the 30-day median is big; 90 days has lots of small ones
        recent = [reel(0, 300_000, 1), reel(1, 310_000, 2), reel(2, 320_000, 3), reel(3, 10_000, 4), reel(4, 11_000, 5)]
        older = [reel(10 + i, 10_000, 40 + i) for i in range(20)]
        s = o.score_creator(recent + older, now=NOW)
        hits = {x["id"]: x for x in s["outliers"]}
        self.assertEqual(set(hits), {"r0", "r1", "r2"})
        self.assertTrue(all(h["baseline_days"] == 90 for h in hits.values()))

    def test_old_reels_outside_90_days_dropped(self):
        m = base_media() + [reel(10, 900_000, days_ago=120)]
        self.assertEqual(o.score_creator(m, now=NOW)["outliers"], [])


class Dedupe(unittest.TestCase):
    def test_same_caption_keeps_best_views(self):
        a, b = reel(1, 1000, caption="Same Caption!"), reel(2, 5000, caption="same caption")
        got = o.dedupe([a, b])
        self.assertEqual([x["id"] for x in got], ["r2"])

    def test_empty_captions_do_not_merge(self):
        self.assertEqual(len(o.dedupe([reel(1, 10, caption=""), reel(2, 20, caption="")])), 2)

    def test_repost_counted_once_in_median(self):
        m = base_media() + [reel(10 + i, 200_000, days_ago=2, caption="same script") for i in range(3)]
        s = o.score_creator(m, now=NOW)
        self.assertEqual(s["reels_30d"], 6)  # three reposts collapse to one
        self.assertEqual(len(s["outliers"]), 1)


class Boosted(unittest.TestCase):
    def test_fixed_line(self):
        self.assertFalse(o.is_boosted(100_000, 1000, None))   # 100 per like
        self.assertTrue(o.is_boosted(100_000, 500, None))     # 200 per like
        self.assertTrue(o.is_boosted(2_000_000, 1000, None))  # over 1,000 per like

    def test_no_likes_is_not_boosted(self):
        self.assertFalse(o.is_boosted(100_000, 0, None))
        self.assertFalse(o.is_boosted(100_000, None, None))

    def test_creator_usual_raises_the_bar(self):
        # this creator always sits near 300 views per like, so 400 is normal for them
        self.assertFalse(o.is_boosted(400_000, 1000, 300))
        self.assertTrue(o.is_boosted(1_000_000, 1000, 100))  # 1000/like > 3 x 100

    def test_usual_ignores_over_1000_and_needs_five(self):
        few = [reel(i, 10_000, likes=100) for i in range(4)]
        self.assertIsNone(o.usual_views_per_like(few))
        five = [reel(i, 10_000, likes=100) for i in range(5)] + [reel(9, 5_000_000, likes=10)]
        self.assertEqual(o.usual_views_per_like(five), 100.0)

    def test_flag_lands_on_outlier(self):
        m = base_media() + [reel(10, 400_000, days_ago=2, likes=100)]  # 4000 per like
        hit = o.score_creator(m, now=NOW)["outliers"][0]
        self.assertTrue(hit["boosted"])


def sample_feed():
    t = lambda d: (NOW - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%S%z")  # noqa: E731
    v = lambda i, c, views, score, d, cap, boosted=False: {  # noqa: E731
        "id": str(i), "creator": c, "url": "https://www.instagram.com/reel/C%d/" % i, "caption": cap,
        "views": views, "likes": 10, "comments": 1, "posted_at": t(d), "outlier_score": score,
        "creator_median_views": 1000, "baseline_days": 30, "boosted": boosted, "code": "C%d" % i}
    return {"generated_at": "2026-10-20T00:00:00+0000",
            "creators": [{"username": "alpha", "followers": 5, "median": 1000, "reels_30d": 9, "outliers": 2},
                         {"username": "beta", "followers": 7, "median": 2000, "reels_30d": 8, "outliers": 1}],
            "videos": [v(1, "alpha", 90_000, 9.0, 2, "Claude Code did this\nsecond line"),
                       v(2, "alpha", 60_000, 4.0, 40, "Old claude code reel"),
                       v(3, "beta", 70_000, 5.0, 3, "\n  Stop using prompts\nmore"),
                       v(4, "beta", 800_000, 50.0, 1, "Paid claude code ad", boosted=True)]}


class Queries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["OUTLIERS_HOME"] = self.tmp.name
        os.environ["OUTLIERS_CREATORS"] = str(Path(self.tmp.name) / "creators.txt")
        o.save_feed(sample_feed())

    def test_search_words_window_and_boosted(self):
        r = mcp.search_all_videos(query="claude code")
        self.assertEqual([v["creator"] for v in r["videos"]], ["alpha"])  # old one outside 30d, paid hidden
        r = mcp.search_all_videos(query="claude code", lookback_days=90, include_boosted=True)
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["videos"][0]["outlier_score"], 50.0)

    def test_search_sort_creator_limit(self):
        r = mcp.search_all_videos(sort="views", limit=1, lookback_days=90)
        self.assertEqual(r["videos"][0]["views"], 90_000)
        self.assertEqual(mcp.search_all_videos(creator="@Beta")["total"], 1)

    def test_top_hooks_returns_first_line_no_boosted(self):
        r = mcp.top_hooks(limit=5)
        self.assertEqual([h["hook"] for h in r["hooks"]],
                         ["Claude Code did this", "Stop using prompts", "Old claude code reel"])
        self.assertEqual(set(r["hooks"][0]), {"hook", "creator", "views", "outlier_score", "url"})

    def test_channel_recap(self):
        r = mcp.channel_recap("@alpha")
        self.assertEqual(r["followers"], 5)
        self.assertEqual(len(r["outlier_videos"]), 2)
        self.assertIn("error", mcp.channel_recap("nobody"))

    def test_channel_recap_hides_paid(self):
        r = mcp.channel_recap("beta")
        self.assertEqual([v["views"] for v in r["outlier_videos"]], [70_000])
        self.assertEqual(r["hidden_boosted"], 1)

    def test_add_channel(self):
        self.assertTrue(mcp.add_channel("@Some.Creator")["ok"])
        self.assertTrue(mcp.add_channel("some.creator")["note"].endswith("already on the watchlist"))
        self.assertEqual(o.read_watchlist(), ["some.creator"])
        self.assertIn("error", mcp.add_channel("bad handle!"))
        self.assertIn("error", mcp.add_channel(""))

    def test_empty_feed_before_first_pull(self):
        os.environ["OUTLIERS_HOME"] = str(Path(self.tmp.name) / "fresh")
        self.assertEqual(mcp.search_all_videos()["total"], 0)


class McpProtocol(unittest.TestCase):
    def test_initialize_list_call(self):
        init = mcp.handle({"id": 1, "method": "initialize", "params": {}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "outliers")
        self.assertIsNone(mcp.handle({"method": "notifications/initialized"}))
        names = [t["name"] for t in mcp.handle({"id": 2, "method": "tools/list"})["result"]["tools"]]
        self.assertEqual(names, ["search_all_videos", "top_hooks", "channel_recap", "add_channel"])

    def test_bad_arguments_and_unknown(self):
        r = mcp.handle({"id": 3, "method": "tools/call", "params": {"name": "channel_recap", "arguments": {}}})
        self.assertTrue(r["result"]["isError"])
        self.assertIn("error", mcp.handle({"id": 4, "method": "tools/call", "params": {"name": "nope"}}))
        self.assertIn("error", mcp.handle({"id": 5, "method": "wat"}))


class FakeGraph:
    calls, usage_pct = 3, 10

    def __init__(self, profiles, limit_after=None):
        self.profiles, self.limit_after, self.n = profiles, limit_after, 0

    def creator(self, h):
        if self.limit_after is not None and self.n >= self.limit_after:
            raise o.RateLimited("slow down")
        self.n += 1
        return self.profiles.get(h, {"error": "110 not found"})


class Pull(unittest.TestCase):
    def test_pull_writes_feed_and_survives_errors_and_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "feed.json"
            media = base_media() + [reel(10, 200_000, days_ago=2)]
            g = FakeGraph({"good": {"name": "G", "followers_count": 9, "media": media}}, limit_after=2)
            logs = []
            o.pull(g, ["example_creator", "good", "private_one", "never_reached"], path=p, log=logs.append)
            feed = json.loads(p.read_text())
            self.assertEqual([c["username"] for c in feed["creators"]], ["good"])
            self.assertEqual(feed["videos"][0]["id"], "r10")
            self.assertTrue(any("placeholder" in m for m in logs))
            self.assertTrue(any("stopped early" in m for m in logs))
            # tracked creator dropped from the watchlist takes their hits with them
            o.pull(g, ["other"], path=p, log=lambda m: None)
            self.assertEqual(json.loads(p.read_text())["videos"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
