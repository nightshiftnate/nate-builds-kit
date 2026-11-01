# sound (keyword: SOUND)

The exact prompt and setup from the "video, music and sound effects in one Claude chat" reel. You connect ElevenLabs to Claude Code with one command, sign in, and ask in plain English. Claude Code writes the prompts, ElevenLabs makes the shot, the music and the sound effects, then joins them into one clip.

## 1. Setup (about 2 minutes)

1. You need Claude Code and an ElevenLabs account. Generating uses your ElevenLabs credits. There's no separate API key.
2. Paste this into your terminal:

```bash
claude mcp add --transport http elevenlabs https://api.elevenlabs.io/v1/mcp
```

3. Open Claude Code and run `/mcp`. Pick `elevenlabs` and sign in with your ElevenLabs account in the browser window that opens.
4. Run `/mcp` again. You should see `elevenlabs` connected.

## 2. The prompt

Paste this into Claude Code. It's also in [prompt.txt](prompt.txt).

```text
Make me a five second vertical clip of a neon diner at night in the rain, with its own music and sound effects.
```

Swap the scene for your own. Keep "five second", "vertical" and "with its own music and sound effects".

## 3. What Claude Code wrote for ElevenLabs

You don't have to write these, Claude does. They're here so you can see what it sent, and reuse them if you want the same look.

- Shot (video model Seedance 2.5, 9:16, 5 seconds, 720p): "Vertical cinematic shot, night, heavy rain on an empty city street. A neon diner sign flickers on, pink and blue light spilling across wet asphalt. Slow push-in toward the diner window, steam rising from a coffee cup inside. Moody, shallow depth of field, film grain."
- Music (5 seconds, instrumental): "Slow late-night lo-fi synth, warm analog pads, soft muted beat, rainy city mood, instrumental."
- Sound effects (5 seconds): "Heavy rain on pavement, distant thunder, a neon sign buzzing and flickering on."

Then ElevenLabs' composition step puts the three together into one clip.

## 4. Fixing one part

If something sounds off, say it in the chat. Mine was:

```text
turn the music down so the rain comes through
```

That changed the music volume in the composition and re-joined the clip. It didn't regenerate anything, so it cost 0 credits.

## 5. What it cost me

16,894 ElevenLabs credits for the whole run, one take each, nothing re-rolled. The video was almost all of it (16,803). Music was 75 and sound effects 17. Ask Claude to estimate first if you want the number before you spend it: the ElevenLabs tools can quote a run without generating.

Video models cost far more than audio, so a longer or higher-resolution shot costs more.

## Links

- [ElevenLabs](https://try.elevenlabs.io/roscozv4ojkx) (this is my affiliate link: if you sign up and pay, I get a cut, and it costs you nothing extra)
- ElevenLabs MCP: the command above. Claude Code docs on MCP: [docs.claude.com](https://docs.claude.com/en/docs/claude-code/mcp)
