# Make Claude Code draw the plan before it builds

From the "Claude Code sketches your reel first" reel. Same vague ask, two Claude Code windows. One builds straight away. The other draws the plan as a flowchart first, so you can fix a scene before anything renders.

## 1. Install merman (free, MIT license)

merman is a Claude Code add-on that draws mermaid diagrams as real flowcharts in the terminal, instead of printing the code. It needs Claude Code 2.1.311 or later. It is not ours: [github.com/iamrohithrnair/merman](https://github.com/iamrohithrnair/merman). Read the code before you install it.

```bash
claude plugin marketplace add iamrohithrnair/merman
claude plugin install merman@merman
```

Then start a new session (or run `/reload-plugins`) and run `/merman setup` to pick a theme.

## 2. The one line

Paste this after your ask:

```
Before you write any code, draw the plan as a mermaid flowchart. One box per scene, with how long it runs. Then stop and wait for my OK.
```

Reply with one sentence to change a box, then say OK and it builds.

## 3. Make it permanent

Add this to your project's `CLAUDE.md` so Claude draws first every time:

```markdown
## Plan first
Before you write any code for a video, animation or multi-step build, draw the plan as a mermaid flowchart: one box per scene or step, with how long it runs. Then stop and wait for my OK. Change the drawing when I ask, and only build after I say OK.
```

## Plan mode vs the drawing

Plan mode (shift+tab) also plans before building, but as text. In our take, plan mode showed the flowchart as code, not as a drawing. The drawing is easier to read when you want to see the whole reel at once.

To turn merman off: `/plugin`, then disable it. Claude Code's own display comes back.
