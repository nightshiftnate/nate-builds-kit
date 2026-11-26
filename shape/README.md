# AI writing has a shape: 8 tells and a check prompt

From the "AI writing has a shape" carousel. Two research teams found that AI writing gives itself away by how it is built, not by which words it uses.

- **StoryScope** (University of Maryland and Google DeepMind) looked at 61,608 short stories. Story structure alone told human from AI fiction at 93.2% (macro-F1). Paper: [arxiv.org/abs/2604.03136](https://arxiv.org/abs/2604.03136)
- **SlopShape** looked at company blog posts. Structure alone scored 98.0 (macro-F1). Paper: [arxiv.org/abs/2609.15369](https://arxiv.org/abs/2609.15369)

## The 8 tells

| # | The tell | The fix |
|---|---|---|
| 1 | The title promises the payoff instead of giving it. | Put the point in the title. |
| 2 | It states its thesis before the first section even starts. | Start with the example. Claim it after. |
| 3 | It announces its own flow: "In this post, we'll cover..." | Cut the roadmap. Just start. |
| 4 | It closes by summing up what it just said. | End on the next step, not a recap. |
| 5 | It talks like an editorial explainer the whole way through. | Write it the way you'd say it. |
| 6 | In stories, it spells out the theme instead of showing it. | Show it. Let the reader name it. |
| 7 | One tidy plot line, told start to finish, in order. | Add a second thread or a flashback. |
| 8 | The check prompt below. | Paste it into Claude with any draft. |

Tells 1 to 5 come from SlopShape. Tells 6 and 7 come from StoryScope.

## The check prompt

Paste this into Claude, then paste your draft under it:

```
Read my draft below. Flag every line that promises a payoff in the title, states the thesis before the first section, announces the flow, ends on a recap, or spells out the theme. Quote each one and give me a plainer rewrite.
```

I wrote the prompt from the two papers' findings. It is not from either paper, and it is not a detector: it points at the lines to fix, and you decide what to change.
