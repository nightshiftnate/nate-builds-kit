# NameThatUI: get the real name for the thing on your screen

From the "Every vibe coder needs this website" carousel.

You can see what you want on screen, but you can't name it, so your prompt comes out vague. [NameThatUI](https://namethatui.com/) fixes that. Describe the thing in your own words and it gives you the real name, plus a prompt you can paste into Claude Code.

It is free, there is no account, and it is made by Fowl Labs, not me.

## How to use it

1. Go to [namethatui.com](https://namethatui.com/).
2. Describe the thing the way you would say it out loud ("the grey shapes while content loads").
3. Open the entry it finds. You get the real name, the other names people use, and a prompt.
4. Paste that prompt into Claude Code, or just use the real name in your own prompt.

## The 7 names from the carousel

Each "you called it" line is quoted word for word from the site.

| You called it | Real name | Entry |
|---|---|---|
| "the dark see-through layer behind a popup" | Scrim (backdrop, overlay) | [/web/scrim](https://namethatui.com/web/scrim) |
| "the grey shapes while content loads" | Skeleton screen | [/web/skeleton-spinner](https://namethatui.com/web/skeleton-spinner) |
| "the little message that pops up in the corner" | Toast (snackbar) | [/web/toast](https://namethatui.com/web/toast) |
| "the text gets cut off with three dots" | Truncation (the dots are an ellipsis) | [/web/truncation](https://namethatui.com/web/truncation) |
| "the gray text inside the box that disappears when you type" | Placeholder | [/web/form-field](https://namethatui.com/web/form-field) |
| "the grid of nine dots in the top corner that opens all your apps" | Waffle menu (app launcher) | [/web/waffle-menu](https://namethatui.com/web/waffle-menu) |
| "the three dots menu" | Overflow menu (meatball or kebab menu) | [/web/three-dots](https://namethatui.com/web/three-dots) |

## The toast prompt

This is the prompt the site's toast page gives you, copied as it appears there:

```
Show a Toast (Snackbar) through a role="status" live region after the action succeeds. Place it in a consistent corner without blocking the page, auto-dismiss only nonessential messages after a short delay, and pause that timer while the toast is hovered or contains keyboard focus.
```

Every entry on the site has its own prompt like this one.
