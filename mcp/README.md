# 4 MCP servers for video work

The four connections from the "4 MCP servers for video work" carousel. Each one lets Claude Code use a tool for you. Open the linked folder for the full setup.

Every command runs from the repo root, after you clone it:

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
```

## 1. Blender

Claude builds and renders scenes in Blender. Needs Blender 5.1+ with the add-on server running first. Run this from the cloned `blender_mcp` folder. Setup: [blender/](../blender/)

```bash
claude mcp add blender -- uv --directory "$PWD/mcp" run blender-mcp
```

## 2. ElevenLabs

Claude makes clips with music and sound effects. You need an ElevenLabs account. Setup: [sound/](../sound/)

```bash
claude mcp add --transport http elevenlabs https://api.elevenlabs.io/v1/mcp
```

## 3. Metricool

Claude reads your reel numbers. This one has no terminal line. In Claude, open Customize, then Connectors, and add Metricool. Setup: [stats/](../stats/)

## 4. Outliers

Finds reels that beat a creator's normal views. Do the Meta setup in the folder first. Setup: [outliers/](../outliers/)

```bash
claude mcp add outliers -s user -- python3 "$PWD/outliers/mcp_server.py"
```
