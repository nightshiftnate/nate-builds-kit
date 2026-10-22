# outliers (keyword: OUTLIERS)

Finds Instagram reels that did far better than the creator's normal, so you can study what worked.

You give it a list of creators. It reads their recent reels from Instagram's official API, works out each creator's usual views, and keeps the reels that beat it by a lot. You search the result from the command line, or ask your own Claude Code about it through an MCP server.

A reel counts as an outlier when both are true:

- Its views are at least 3x the creator's median reel views over the last 30 days (or over the last 90 days, see hot streaks below).
- It has at least 50,000 views.

One Python package, standard library only, Python 3.9 or newer. No AI model inside it, no paid service.

## How it scores

- Score = the reel's views divided by the creator's median reel views over the last 30 days. A 5 means five times their usual.
- A creator needs at least 5 reels in 30 days. With fewer there is no fair "usual" to compare against, so they get no outliers.
- Reels with 0 views are ignored.
- If the same caption was posted more than once, it counts once, at its best view count.
- Hot streaks: if most of a creator's month was big reels, their 30-day usual is itself big and a new hit reads low. So a reel also counts at 3x the creator's median over the last 90 days. Each hit says `baseline_days` (30 or 90) so you know which one it used. If a creator's views jumped up and stayed up, a few ordinary new reels can show up as 90-day hits for a while. Check their other recent reels before copying one.
- Likely paid reels are marked `boosted` and hidden unless you ask. Instagram leaves likes on promoted copies out of the like count, so a paid reel has far more views per like than normal. A reel is marked when its views per like are more than 3x the creator's usual (and over 150), or over 1,000 for anyone. If a creator hides likes there is no like count to check, so their paid reels can't be spotted and show up like any other hit.
- A hit stays in your feed after it is older than 30 days, as long as the creator stays on your list. Searches look back 30 days unless you ask for more.

## Setup

### 1. Meta side (once)

You need a Meta developer app that can read other creators' public data. All of this is free.

1. An Instagram Business or Creator account (a "professional" account), connected to a Facebook Page.
2. A Meta developer account and an app. In the App Dashboard, add Facebook Login for Business.
3. Get a user access token with these permissions: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement` (Meta lists all three for the Business Discovery call). If your Page role comes through Business Manager, Meta also asks for `ads_management` or `ads_read`. Graph API Explorer in the App Dashboard can generate this token.
4. Make it long-lived (about 60 days). Do this call somewhere private, because it includes your app secret:

   ```
   GET https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN
   ```

   Set a reminder to redo it before it expires. An expired token can't be exchanged. Meta also says a Page token made from a long-lived user token has no expiry date, but this tool has only been checked with a user token.
5. Find your Instagram account's ID: call `GET /me/accounts` to get your Page ID, then `GET /{page-id}?fields=instagram_business_account`. The `id` in that answer is your `IG_USER_ID`.

Things to know:

- Business Discovery only reads other professional accounts (Business or Creator). Personal accounts, and age-gated accounts, come back as errors or nothing. The tool skips them and says so.
- Meta says Standard Access (the default for a new app) is meant for apps used only by people who have a role on the app, so your own account on your own app doesn't need App Review for that. Meta's Business Discovery pages don't say whether the call works in that mode, so try one creator first. If you get a permissions error, that is the thing to look into. Advanced Access (App Review plus Business Verification) is what you need if other people's accounts will use your app.
- Meta puts this call under its Platform Rate Limits and doesn't publish the call count for user tokens. The tool reads the usage headers Meta sends back and stops cleanly at 80% of the hourly budget, saving what it already got. Run `pull` again later to continue. It also caps itself at 180 calls per run.

Meta's pages used: see "Sources" at the bottom.

### 2. Keys

Credentials come from environment variables only. Nothing is written to a file.

```bash
export IG_USER_ID="your instagram professional account id"
export IG_ACCESS_TOKEN="your long-lived token"
```

### 3. Your list

Edit `outliers/creators.txt`. One Instagram handle per line, no @. It ships with two placeholder lines that are skipped until you replace them.

### 4. Pull

From the repo root:

```bash
python3 outliers/outliers.py pull
```

It writes `~/.outliers/feed.json`, creating the folder the first time. Set `OUTLIERS_HOME` to keep it somewhere else. Run `pull` whenever you want fresh numbers (once a week is plenty).

## Use it from the command line

```bash
python3 outliers/outliers.py search "claude code"
python3 outliers/outliers.py search "claude code" --days 90 --sort views --limit 5
python3 outliers/outliers.py hooks
python3 outliers/outliers.py recap somecreator
python3 outliers/outliers.py add somecreator othercreator
```

## Use it from Claude Code

Register the MCP server once, from the repo root:

```bash
claude mcp add outliers -s user -- python3 "$PWD/outliers/mcp_server.py"
```

Restart Claude Code, then type `/mcp` and check that `outliers` shows as connected. Ask in plain words:

- "Search outliers for AI agents from the last 30 days, best first."
- "Show me the top hooks in the outlier feed and label the format of each."
- "Recap @somecreator."
- "Add @somecreator to the outlier watchlist."

| Tool | What you get |
|---|---|
| `search_all_videos` | Outlier reels filtered by words, score, views, days or creator |
| `top_hooks` | The top hits by score, each with its first caption line, creator, views and score |
| `channel_recap` | One creator's followers, usual views and outlier reels |
| `add_channel` | Adds a creator to `creators.txt` for the next pull |

`top_hooks` has no model behind it. It hands your Claude Code the opening lines, and your Claude Code names the hook format.

## Limits

- Instagram only, reels only.
- The hook is the first line of the caption, not what is said in the video. There is no transcription.
- Instagram doesn't share saves or shares for other people's accounts.
- Scores use today's view counts on both sides. A reel posted last week is compared with reels that had longer to grow, so brand new reels can read low.
- The 90-day check only sees what one pull reaches: up to 5 pages of 50 posts per creator.

## Tests

```bash
python3 -m pytest outliers
```

or without pytest: `python3 outliers/test_outliers.py`. They use made-up reels and no network.

## Undo

Delete `~/.outliers/` to remove the stored feed. Delete the folder and run `claude mcp remove outliers -s user` to remove the rest.

## Sources

Meta's own docs, checked when this was written:

- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery
- https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery
- https://developers.facebook.com/docs/instagram-platform/overview
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/get-started
- https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived
- https://developers.facebook.com/docs/graph-api/overview/rate-limiting
