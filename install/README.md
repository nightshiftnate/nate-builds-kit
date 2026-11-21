# 4 Claude Code skills to install now

The four skills from the "4 Claude Code skills to install now" carousel. Three are made by other people, and each one is credited below. Restart Claude Code after you install one.

## 1. HyperFrames

Claude Code learns to render motion graphics. Made by HeyGen. Setup: [studio/](../studio/)

```bash
npx hyperframes skills
```

## 2. draw-beautiful

Turns a photo into a bank note engraving. Made by bumicodes (MIT license): [github.com/bumicodes/draw-beautiful](https://github.com/bumicodes/draw-beautiful). My use of it: [engrave/](../engrave/)

```bash
npx skills add bumicodes/draw-beautiful -g -a claude-code
```

## 3. humanizer

Rewrites stiff AI text so it sounds like you. Made by blader (MIT license): [github.com/blader/humanizer](https://github.com/blader/humanizer). Needs Claude Code 2.1.142 or newer. Run these inside Claude Code, then type `/humanizer`.

```
/plugin marketplace add blader/humanizer
/plugin install humanizer@humanizer
```

## 4. overnight

Type /overnight. It works till 6:15 and leaves a summary. This one is mine. Setup: [overnight/](../overnight/)

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
mkdir -p ~/.claude/skills/overnight && cp overnight/SKILL.md ~/.claude/skills/overnight/SKILL.md
```
