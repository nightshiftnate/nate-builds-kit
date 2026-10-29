# blender (keyword: BLENDER)

Both prompts from the "Plan your camera move in Blender" reel. The first has Claude Code build a grey-box scene in Blender and render a five-second clip. The second hands that clip to an AI video model as the camera reference, so the AI isn't guessing the camera move.

## 1. Setup (about 10 minutes)

1. Install Blender, free, from [blender.org](https://www.blender.org/download/). The add-on needs Blender 5.1 or newer. I used 5.2.
2. Install the official Blender MCP add-on from [blender.org/lab/mcp-server](https://www.blender.org/lab/mcp-server/). That page has two ways: drag the add-on link into Blender (do it twice, once to add the Blender Lab repository and once to install), or download the zip and use Install from Disk in Blender's extension preferences.
3. In Blender's preferences, open the MCP add-on and start its server. Claude Code talks to Blender through that local connection, so Blender has to be open with the server running.
4. Get the MCP server and connect it to Claude Code. This is what I ran on my Mac. It needs [uv](https://docs.astral.sh/uv/) (`brew install uv`) and git:

```bash
git clone https://projects.blender.org/lab/blender_mcp.git
cd blender_mcp
claude mcp add blender -- uv --directory "$PWD/mcp" run blender-mcp
```

5. Check it with `claude mcp list`. You should see `blender` with a green check. If Claude Code was already open, restart it.

The Blender page warns that this runs code Claude writes inside Blender with no safeguards. Don't run it on a machine with anything sensitive open, and save your Blender file first.

## 2. Prompt 1: the Blender scene

Open Claude Code with Blender running and paste this. It's also in [prompt-1-blender.txt](prompt-1-blender.txt).

```text
Using Blender, build a grey-box scene: a straight street with boxes on both sides as buildings, and an orange mannequin walking down the middle. Add one camera that starts low behind the mannequin and cranes up and around to its right side, always aimed at it. Five seconds, vertical. Render it to an mp4.
```

You get a five-second vertical grey-box clip. Watch it. If the camera move isn't what you wanted, tell Claude one change at a time ("start lower", "swing wider") and render again. This clip is your camera plan.

## 3. Prompt 2: the AI video

This part is paid. I used HeyGen's reference to video, and a five-second clip cost 10 credits. Upload the grey-box clip from step 2 as the reference, then paste this. It's also in [prompt-2-heygen.txt](prompt-2-heygen.txt).

```text
Cinematic live-action shot. A young man in a dark hooded jacket walks down a narrow rainy city street at dusk, between tall buildings with glowing shop signs. Match the camera motion of the reference video exactly: start low behind him, then rise and swing around to his right side, always keeping him centered in frame. Replace the orange mannequin with the man and the grey boxes with real buildings. Realistic lighting, wet pavement reflections, shallow depth of field.
```

Swap the description for your own scene. Keep the line about matching the camera motion.

## What to expect

The AI shot follows the camera path roughly. It is not frame perfect. In my run the swing around the man came out shorter than the one in Blender. What you gain is that the camera move is planned instead of left to the model's guess.

## Cost

Blender and the add-on are free. Claude Code is whatever plan you're already on. The HeyGen step is the only paid part: 10 credits for a five-second clip.

## Undo

`claude mcp remove blender`, then delete the cloned `blender_mcp` folder and disable the add-on in Blender's preferences.
