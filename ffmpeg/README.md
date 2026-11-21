# 6 prompts that run ffmpeg

The six prompts from the "6 prompts that run ffmpeg" carousel. Paste one into Claude Code with the file in your folder. I ran the command for each one on a test clip (ffmpeg 9.0.2) before putting it here.

You need ffmpeg installed. Captions (prompt 6) need a build with the subtitles filter. Plain Homebrew `ffmpeg` doesn't have it, `ffmpeg-full` does.

## 1. Vertical

```
Use ffmpeg to turn clip.mp4 into a 9:16 vertical video, 1080 by 1920, cropped from the center.
```

Claude ran `crop=ih*9/16:ih,scale=1080:1920`. Result: a 1080x1920 file.

## 2. GIF

```
Use ffmpeg to make a GIF from seconds 1 to 4 of clip.mp4, 15 frames per second, 480 pixels wide.
```

Claude ran `-ss 1 -t 3 -vf "fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"`. Result: 480x270, 45 frames, 457 KB.

## 3. Loudness

```
Use ffmpeg to normalize the loudness of clip.mp4 to -16 LUFS and leave the video untouched.
```

Claude ran `-c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac`. Result: -21.8 LUFS became -16.0 LUFS.

## 4. Compress

```
Use ffmpeg to shrink clip.mp4 for upload: H.264, CRF 28, AAC audio, and start playing right away.
```

Claude ran `-c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k -movflags +faststart`. Result on my small test clip: 200,740 bytes down to 176,326. Bigger real clips shrink more.

## 5. Silence

```
Use ffmpeg to find silences longer than half a second in gap.mp4 and cut them out of the audio and the video.
```

This takes two steps. First `silencedetect=noise=-40dB:d=0.5` finds the gaps (mine was 2s to 4s). Then `select='lt(t,2)+gte(t,4)',setpts=N/FRAME_RATE/TB` with `aselect='lt(t,2)+gte(t,4)',asetpts=N/SR/TB` keeps everything else. Result: 6.0s became 4.0s, audio and picture still in sync.

## 6. Captions

```
Use ffmpeg to burn the captions in cap.srt into clip.mp4.
```

Claude ran `-vf "subtitles=cap.srt:force_style='FontSize=28,Outline=2'" -c:a copy` with `ffmpeg-full`. Result: captions burned into the picture, checked on a frame.
