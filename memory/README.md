# Make Claude and ChatGPT remember you

From the "Stop re-explaining yourself to Claude" carousel.

Set these up once and you stop typing the same background into every new chat.

## Claude

### Memory

Memory is on by default for Free, Pro, Max and Ultra plans on the web, Claude Desktop and Claude Mobile.

To check it, go to **Settings**, then **Your Claude** (in the older Settings layout it's **Settings**, then **Memory**). Make sure **Generate memory from chats** is on.

### Projects

Give each big job its own Project, so its files and instructions stay together. Projects are available to all users. Free users can create up to five.

### Incognito chats

For something you don't want remembered, start an Incognito chat with the ghost icon in the upper right. Incognito chats aren't saved to your chat history or to Claude's memory. They work on all plans.

### Claude Code

In a project folder, run:

```
/init
```

It writes a starting CLAUDE.md file. Claude reads CLAUDE.md at the start of every session, so it's the place to write down whatever you'd otherwise re-explain. Claude Code also keeps its own auto memory in local sessions, on by default.

## ChatGPT

### Saved memories

Just tell it: "Remember that I..." OpenAI's help page: "Saved memories are details that you explicitly ask ChatGPT to remember."

### Custom instructions

Set them once and every chat uses them. Custom instructions are available on all plans on web, desktop, iOS and Android.

1. On web or desktop, go to **Settings**, then **Personalization**. On iOS or Android, go to **Settings**, then **Customize ChatGPT**.
2. Make sure **Enable customization** is on.
3. Type your instructions in the **Custom Instructions** field.

## Starter prompt

Paste this into ChatGPT's custom instructions, or into a Claude Project's instructions, and fill in the brackets:

```
I'm a [job]. I work on [projects]. Keep answers short and ask before you assume.
```

## Sources

- Claude Help Center, memory: https://support.claude.com/en/articles/11817273
- Claude Help Center, Projects: https://support.claude.com/en/articles/9517075
- Claude Help Center, Incognito chats: https://support.claude.com/en/articles/12260368
- Claude Code docs, memory: https://code.claude.com/docs/en/memory
- OpenAI Help Center, memory: https://help.openai.com/en/articles/8590148
- OpenAI Help Center, custom instructions: https://help.openai.com/en/articles/8096356

Checked against these pages on 26 November 2026. Apps change their menus, so if a name is different, look for "memory" or "personalization" in settings.
