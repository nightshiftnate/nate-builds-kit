"""The outlier feed as an MCP server, so Claude Code can search it. Standard library only.

Register once (from the repo root):
  claude mcp add outliers -s user -- python3 "$PWD/outliers/mcp_server.py"

Protocol: MCP over stdio, newline-delimited JSON-RPC 2.0 (initialize, tools/list, tools/call, ping).
It reads the feed file fresh on every call, so a new pull shows up without a restart.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outliers as core  # noqa: E402

PROTOCOL = "2025-06-18"


def search_all_videos(query="", min_outlier_score=3.0, min_views=0, lookback_days=30, creator="",
                      include_boosted=False, sort="outlier_score", limit=10):
    s = {"views": "views", "recent": "recent"}.get(sort, "score")
    return core.search(core.load_feed(), query, min_outlier_score, min_views, lookback_days, creator,
                       include_boosted, s, limit)


def top_hooks(limit=10):
    return core.top_hooks(core.load_feed(), limit)


def channel_recap(creator):
    return core.channel_recap(core.load_feed(), creator)


def add_channel(username):
    return core.add_channel(username)


S, I, N, B = ({"type": "string"}, {"type": "integer"}, {"type": "number"}, {"type": "boolean"})
TOOLS = {
    "search_all_videos": (search_all_videos,
                          "Search outlier Instagram reels from the watchlist (views at least 3x the creator's "
                          "30-day median, or 3x their 90-day median during a hot streak, and at least 50,000; "
                          "each hit's baseline_days says which). Matches words in the caption or creator. "
                          "Reels stay in the feed after 30 days; raise lookback_days to see older ones.",
                          {"query": S, "min_outlier_score": N, "min_views": I, "lookback_days": I, "creator": S,
                           "include_boosted": B, "sort": {"type": "string", "enum": ["outlier_score", "views", "recent"]},
                           "limit": I}, []),
    "top_hooks": (top_hooks,
                  "The top outlier reels by score, each with its first caption line, creator, views and score. "
                  "No model behind it: read the lines and label the hook format yourself.",
                  {"limit": I}, []),
    "channel_recap": (channel_recap, "One watched creator: followers, usual views, and their outlier reels (likely paid ones hidden, counted in hidden_boosted).",
                      {"creator": S}, ["creator"]),
    "add_channel": (add_channel, "Add an Instagram creator to the watchlist. They are scored on the next pull.",
                    {"username": S}, ["username"]),
}


def handle(msg):
    mid, method, p = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:
        return None  # notification
    if method == "initialize":
        res = {"protocolVersion": p.get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
               "serverInfo": {"name": "outliers", "version": "1.0"}}
    elif method == "ping":
        res = {}
    elif method == "tools/list":
        res = {"tools": [{"name": n, "description": d,
                          "inputSchema": {"type": "object", "properties": props, "required": req}}
                         for n, (_, d, props, req) in TOOLS.items()]}
    elif method == "tools/call":
        t = TOOLS.get(p.get("name"))
        if not t:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool %s" % p.get("name")}}
        try:
            out, err = t[0](**(p.get("arguments") or {})), False
        except Exception as e:  # bad argument: tell the model, keep the server alive
            out, err = {"error": "%s: %s" % (type(e).__name__, e)}, True
        res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}], "isError": err}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: %s" % method}}
    return {"jsonrpc": "2.0", "id": mid, "result": res}


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            out = handle(json.loads(line))
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if out:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
