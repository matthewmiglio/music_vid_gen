---
name: generate-music-video
description: Turn a song file into a rendered, beat-synced HyperFrames music video. Analyzes the song (scripts/analyze_song.py + /analyze-audio), picks a visual concept that fits it, builds a new project in projects/, renders it to output/. Use when the user runs /generate-music-video <song> [length], or asks to make a music video / visualizer for a song.
---

# generate-music-video

```
/generate-music-video <path to song> [length]
```

- `length`: default `30` (seconds). Also accepts `whole` / `whole song`, a number of seconds (`45`), or `M:SS` (`1:15`).
- The user may also say where to start ("start at 1:12"). Pass that as `--start`.

All paths below are relative to the repo root (the folder holding this `.claude/`).

## 1. Scaffold the project

Slug = song file stem, lowercased, spaces → `-`, plus `-v<N>` using the next free N in `projects/` (e.g. `luvme-v1`, `luvme-v2`). Every run makes a new project. Never overwrite an old one.

```bash
HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init projects/<slug> --example blank --non-interactive
```

## 2. Analyze the song (numbers)

```bash
python scripts/analyze_song.py "<song>" --length <length> [--start <M:SS>] -o projects/<slug>
```

It prints a summary and writes to the project:

| File | Contents |
| --- | --- |
| `analysis.json` | Everything about the whole song: BPM, beats, downbeats, key, chords per bar, loudness (LUFS), stereo, timbre, band balance, sections, drops, breakdowns, accents, energy per second, and the `clip` window. |
| `song-data.js` | `window.SONG` (clip-relative seconds: `beats`, `downbeats`, `drops`, `breakdowns`, `accents`, `sections`, `chord_changes`, `energy_per_second`, `bpm`, `bar_seconds`, `key`, `title`) and `window.AUDIO_DATA` (`fps`, `totalFrames`, `frames[i].rms`, `frames[i].bands[0..15]`, bass to treble, 0-1). |
| `audio.wav` | The trimmed clip with short fades. This is the video's soundtrack. |

Sanity-check the summary before building:
- **BPM** may be half or double the real tempo. If the song feels twice as fast as the reported BPM (common in trap), plan motion on `double_time`; the beat list is still usable.
- **No drops detected** is normal for ambient or lo-fi songs. Build the arc from `sections` and `energy_per_second` instead.
- If the auto-picked clip starts somewhere dull, re-run with `--start`.

## 3. Analyze the song (feel) with /analyze-audio

Run it on the **clip** (`audio.wav`), not the full song. It's cheaper, and it describes the part that's actually in the video:

```bash
python "C:/Users/matt/.claude/skills/analyze-audio/analyze_audio.py" projects/<slug>/audio.wav --question "Describe this track for a music-video director: genre and subgenre, mood and emotional arc, vocal presence and delivery (and any lyrics you can make out), standout sounds, how the energy moves across the clip, and 3 visual worlds (settings, textures, color palettes, imagery) that would match it. Be concrete."
```

Save the output to `projects/<slug>/gemini-analysis.md`. Treat its key, chord and plugin claims as guesses (the numbers from step 2 win). Trust it on mood, genre and imagery.

## 4. Choose the concept

Write `projects/<slug>/DESIGN.md` before any HTML (the HyperFrames skill requires it):

- `## Concept`: one paragraph. A specific visual world taken from the song's feel, not "abstract shapes that pulse". Pick one of Gemini's worlds or a better one. Use the song title in the concept if it helps (e.g. `trappin-in-japan` → neon Tokyo signage, kanji, rain).
- `## Colors`: 3-5 hex values with roles, taken from the mood (dark and slowed → deep, desaturated; bright pop → saturated).
- `## Typography`: 1-2 font families.
- `## Timeline`: a table mapping the clip's timeline to scenes. Scene cuts land on **downbeats**. The biggest visual change lands on the **first drop** (or the highest-energy section start when there's no drop). Breakdowns get stripped-back visuals. Scene length follows tempo: roughly 2-4 bars per scene at 30s, longer for ambient songs.
- `## Audio mapping`: which signal drives which property (e.g. `bands[0-1]` bass → background scale, `rms` → glow, `accents` → flash or shake, `beats` → small pulse on the title, `chord_changes` → color shift).
- `## What NOT to Do`: include the audio-reactive bans below plus 2-3 concept-specific ones.

**Make each video different.** Before choosing, list the existing `projects/*/DESIGN.md` concepts and don't repeat a palette, layout or core idea from another video of the **same** song.

## 5. Build the composition

Load the `hyperframes`, `hyperframes-core`, `hyperframes-creative` (read `references/audio-reactive.md`), and `hyperframes-animation` skills before writing HTML, and follow their rules (deterministic, one paused timeline registered on `window.__timelines`, entrance animations, transitions between scenes, no `repeat: -1`).

Project-specific wiring for `projects/<slug>/index.html`:

```html
<head>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script src="song-data.js"></script> <!-- loads synchronously: SONG + AUDIO_DATA -->
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0"
       data-duration="<SONG.duration>" data-width="1920" data-height="1080">
    <audio id="music" data-timeline-role="music" src="audio.wav"
           data-start="0" data-duration="<SONG.duration>" data-track-index="0" data-volume="1"></audio>
    <!-- scenes / clips -->
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    // Scenes: build from SONG.downbeats / SONG.drops / SONG.sections, not hard-coded guesses.
    // Beat pulse:  SONG.beats.forEach(t => tl.fromTo(".title", {scale:1.04}, {scale:1, duration:0.25, ease:"power2.out"}, t));
    // Per-frame audio reactivity (one tl.call per frame):
    for (let f = 0; f < AUDIO_DATA.totalFrames; f++) {
      const fr = AUDIO_DATA.frames[f];
      tl.call(() => { /* gsap.set(...) from fr.rms / fr.bands */ }, [], f / AUDIO_DATA.fps);
    }
    window.__timelines["main"] = tl;
  </script>
</body>
```

- Write `data-duration` as the literal number from `SONG.duration`; attributes can't read JS.
- Don't let the same property on the same element be driven by both a per-frame `gsap.set` and a tween. Split them across a wrapper and its child.
- Audio-reactive bans (from the HyperFrames guide): no equalizer bars, spectrum analyzers, waveforms, music-note clip art, generic particle fields, rainbow cycling, white strobes on every beat, or abstract pulsing orbs. Audio drives *behavior*; the concept drives *what's on screen*.
- Text: the song title (from the filename, cleaned up) belongs somewhere, usually the intro. Keep text pulses to 3-6% scale; backgrounds can swing 10-30%.
- Visuals must be self-contained: CSS, SVG, canvas or WebGL drawn in the page. Only use a registry block (`hyperframes-registry` skill) or generated image (`/generate-image`) if the concept really needs it; save any asset into the project folder.
- Deterministic randomness: a seeded PRNG (mulberry32), never `Math.random()`.

## 6. Check, render, verify

```bash
npx hyperframes lint projects/<slug>
npx hyperframes check projects/<slug>
npx hyperframes render projects/<slug> -o output/<slug>.mp4 --quality standard
```

Fix every lint error and layout/contrast issue before rendering. Then verify the actual video:

1. `ffprobe` the MP4: duration matches `SONG.duration` (±0.1s) and there is an audio stream.
2. Pull 5-6 frames with ffmpeg into `projects/<slug>/qa/`: 1s in, just before and just after the first drop, the middle, and 1s before the end. Look at them (Read the PNGs). Blank frames, overflowing text, or a drop that doesn't look different from the build-up are bugs. Fix them and re-render.

```bash
ffmpeg -y -loglevel error -ss <t> -i output/<slug>.mp4 -frames:v 1 projects/<slug>/qa/<t>.png
```

## 7. Report

Tell the user: output path, clip window used (start → end in the song), BPM/key, the concept in one sentence, and how the drop is handled. Don't open the video for them; they'll open it themselves.
