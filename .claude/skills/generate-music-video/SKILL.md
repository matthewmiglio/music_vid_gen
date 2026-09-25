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
python "C:/Users/matt/.claude/skills/analyze-audio/analyze_audio.py" projects/<slug>/audio.wav --question "Describe this track for a music-video director: genre and subgenre, mood and emotional arc, vocal presence and delivery (and any lyrics you can make out), standout sounds, how the energy moves across the clip, and the textures, materials, colors, shapes and motions it evokes (not scenes or locations). Be concrete." > projects/<slug>/gemini-analysis.md
```

(Only stdout goes to the file; token usage prints on stderr.) Treat its key, chord and plugin claims as guesses (the numbers from step 2 win). Trust it on mood, genre and texture. Ignore any settings, locations or camera moves it suggests anyway (it keeps offering "late-night driving", "wet asphalt" and neon); those lead straight to the banned journey look.

## 4. Choose the concept

### 4a. Pick an archetype nobody has used recently

Diversity across the whole library matters more than any single video. The failure to avoid: every video becoming "first-person trip at night through rain past glowing signs". Left alone, that's the default, so it's banned (see below).

1. Run `grep -h "^Archetype:" projects/*/DESIGN.md` to see which archetypes are already used, across **all** songs.
2. Pick one from this table that is **not** in that list. If every one has been used, pick the least-used one. You may also invent a new archetype, if it is clearly unlike everything in the table and in the used list; give it a short kebab-case name. Choose the one that best fits the song's mood from Gemini's analysis, not the easiest one.

| Archetype | What it looks like | Camera |
| --- | --- | --- |
| `kinetic-type` | The words are the visuals: huge type that stacks, slices, stretches, and swaps on beats. Lyrics (from Gemini) and the song title carry it. | static, flat |
| `swiss-poster` | A grid-based graphic-design poster that rebuilds itself: bold blocks, rules, numbers, one or two flat colors on paper white. | static, flat |
| `paper-collage` | Cut paper, torn edges, halftone photo scraps and tape; pieces slide and flip in stop-motion steps (hold frames, snap movement). | static, flat |
| `macro-material` | Extreme close-up of a material reacting to sound: ink blooming in water, molten metal, wet paint, frost, smoke through light. | slow push-in |
| `tabletop-still-life` | Objects on a surface seen from above (records, fruit, tools, tarot cards), rearranged beat by beat. | top-down |
| `blueprint-diagram` | Technical drawing or schematic that draws itself: line work, measurements, callouts, exploded views of something tied to the song. | static, pans across a drawing |
| `retro-interface` | A fake old screen: CRT terminal, 8-bit game, Windows 98 desktop, VHS menu, pager or old phone. The song plays "inside" it. | static |
| `op-art-geometry` | Bauhaus/op-art pattern systems: stripes, checkerboards, moiré and interlocking shapes that shift phase with the music. No glowing orbs. | static, flat |
| `illustrated-character` | A drawn figure with a tiny story across the clip, in an adult graphic-novel, ink or anime-adjacent style. Never a mascot or cartoon critter. | follows the character |
| `nature-growth` | Something organic grows, blooms, spreads or decays in time with the song: vines, coral, mold, crystals, roots. | static or slow |
| `cosmic-scientific` | Orbital diagrams, star charts, cells under a microscope, particle-chamber tracks; clinical labels and a scientific look. | static or slow zoom |
| `textile-pattern` | Woven, knitted or printed pattern that unravels and re-weaves; quilt blocks, tartan, embroidery stitches. | static, flat |
| `architectural-iso` | An isometric building, room or tiny city that assembles, lights up and rearranges. | fixed isometric |
| `photo-sequence` | A found-photo or film-contact-sheet look: frames, sprocket holes, date stamps, flash exposures, developing prints. | static, flat |
| `journey-pov` | Moving through a space (road, tunnel, street, corridor). **Only when every other archetype is used, and never with night + rain + neon signs.** | forward motion |

Also vary these from the most recent project (`ls -t projects | head -2`, then read its DESIGN.md): **light vs dark canvas** (use a light canvas at least one time in three), **camera** (static/flat vs moving), and **main color**.

### 4b. Rules for every concept

- **Don't base the concept on the song title.** File names are working titles and are usually meaningless or misleading. Only use the title when it names something concrete and visual, such as a place or an object ("japan" can suggest Japanese type or a Tokyo palette). Titles like "luvme", "safe2" or "clams" must not drive the imagery: no hearts for a song called "luv", and no clams for "clams". Putting the title on screen as text is fine; building the visuals around its literal meaning is not.
- **No childish or cute looks.** Avoid cartoon mascots, balloon or inflatable shapes, bouncy squash-and-stretch toys, candy or pastel-toy palettes, googly eyes, rounded bubble fonts, and anything that reads as a kids' app or a birthday card. Aim for work that could be album art, a fashion editorial, a gallery piece or a design-studio reel: stylish, confident and adult. Playful is fine; juvenile is not.

### 4c. Write DESIGN.md

Write `projects/<slug>/DESIGN.md` before any HTML (the HyperFrames skill requires it). The first line must be `Archetype: <name from the table>`.

- `## Concept`: one paragraph. A specific idea within the archetype that comes from **how the song sounds and feels** (Gemini's mood and texture notes, tempo, energy, key). For example, a slow, dark, detuned track as `macro-material` could be black ink bleeding through wet paper, with each 808 hit pushing a new bloom outward. Not "abstract shapes that pulse".
- `## Colors`: 3-5 hex values with roles, taken from the mood (dark and slowed → deep, desaturated; bright pop → saturated).
- `## Typography`: 1-2 families. Prefer these fonts, which work with no setup (some are built in; the rest are fetched from Google Fonts automatically at check and render time): Montserrat, Oswald, League Gothic, Archivo Black, Space Mono, IBM Plex Mono, JetBrains Mono, Source Code Pro, Noto Sans JP (see `hyperframes-creative/references/typography.md`). For anything else, copy a `.ttf` into `projects/<slug>/fonts/` and declare it with `@font-face`, or lint fails with `font_family_without_font_face`.
- `## Timeline`: a table mapping the clip's timeline to scenes. Scene cuts land on **downbeats**. The biggest visual change lands on the **first drop** (or the highest-energy section start when there's no drop). Breakdowns get stripped-back visuals. Scene length follows tempo: roughly 2-4 bars per scene at 30s, longer for ambient songs.
- `## Audio mapping`: which signal drives which property (e.g. `bands[0-1]` bass → background scale, `rms` → glow, `accents` → flash or shake, `beats` → small pulse on the title, `chord_changes` → color shift).
- `## What NOT to Do`: include the audio-reactive bans below plus 2-3 concept-specific ones.

## 5. Build the composition

Load the `hyperframes`, `hyperframes-core`, `hyperframes-creative` (read `references/audio-reactive.md` and `references/typography.md`), and `hyperframes-animation` skills before writing HTML, and follow their rules (deterministic, one paused timeline, entrance animations, transitions between scenes, no `repeat: -1`). **This skill owns the workflow:** skip the `hyperframes` skill's intake interview, `BRIEF.md`, and its routing to `/music-to-video`. DESIGN.md from step 4 is the brief.

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
    // Keep this line even though hyperframes-core calls it optional: lint 0.7.x fails without it
    // (timeline_registry_missing_init). If you wrap the script in an IIFE, put it inside.
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    // Scenes: build from SONG.downbeats / SONG.drops / SONG.sections, not hard-coded guesses.
    // Beat pulse:  SONG.beats.forEach(t => tl.fromTo(".title", {scale:1.04}, {scale:1, duration:0.25, ease:"power2.out"}, t));
    // Per-frame audio reactivity: one driver tween, one draw per rendered frame.
    const driver = { t: 0 };
    tl.to(driver, { t: SONG.duration, duration: SONG.duration, ease: "none", onUpdate() {
      const f = Math.min(AUDIO_DATA.totalFrames - 1, Math.floor(driver.t * AUDIO_DATA.fps));
      draw(AUDIO_DATA.frames[f], driver.t);  // gsap.set(...) / canvas paint from fr.rms, fr.bands
    } }, 0);
    window.__timelines["main"] = tl;
  </script>
</body>
```

- Write `data-duration` as the literal number from `SONG.duration`; attributes can't read JS.
- Don't let the same property on the same element be driven by both the per-frame `draw` and a tween. Split them across a wrapper and its child.
- Give every scene `.clip` explicit `position:absolute; inset:0`. Without it the clip can collapse into the top-left corner and `check` reports confusing overlaps. Because clips then fill the frame, scaling a clip pivots on the frame's center: set `transformOrigin` explicitly or scale an inner element.
- Stacked display lines need `line-height` of at least 1.1, or `check` reports text overlapping.
- Motion that is supposed to leave the frame or overlap (wipes, fly-offs) gets flagged by `check`. Mark those elements with `data-layout-allow-overflow` / `data-layout-allow-occlusion` rather than changing the design.
- SVG filters (lighting, blur, turbulence) on an SVG that is scaled up render blurry and blocky. Draw large shapes at their real pixel size instead of scaling a small viewBox.
- Audio-reactive bans (from the HyperFrames guide): no equalizer bars, spectrum analyzers, waveforms, music-note clip art, generic particle fields, rainbow cycling, white strobes on every beat, or abstract pulsing orbs. Audio drives *behavior*; the concept drives *what's on screen*.
- Text: the song title (from the filename, cleaned up) belongs somewhere, usually the intro. Keep text pulses to 3-6% scale; backgrounds can swing 10-30%.
- Visuals must be self-contained: CSS, SVG, canvas or WebGL drawn in the page. Only use a registry block (`hyperframes-registry` skill) or generated image (`/generate-image`) if the concept really needs it; save any asset into the project folder.
- Deterministic randomness: a seeded PRNG (mulberry32), never `Math.random()`.
- A single large `index.html` triggers the lint warning `composition_file_too_large`. It's harmless and can be ignored.
- `energy_per_second` is more detailed than `sections`. Check it for silence (values near 0), such as a song that ends early, so you don't animate over nothing.

## 6. Check, preview, render, verify

```bash
npx hyperframes lint projects/<slug>
npx hyperframes check projects/<slug>
npx hyperframes snapshot projects/<slug> --at 1,<pre-drop>,<post-drop>,<mid>,<end-1> --no-end --describe false
```

Fix every lint error and every layout and contrast issue from `check`, including contrast warnings. Then look at the snapshot PNGs in `projects/<slug>/snapshots/`, which is much cheaper than a render. Fix anything wrong and snapshot again. When the frames look right, render:

```bash
mkdir -p output
npx hyperframes render projects/<slug> -o output/<slug>.mp4 --quality standard --quiet
```

(If several renders run at once, add `--workers 3` to each.) Then verify the actual video:

1. `ffprobe` the MP4: duration matches `SONG.duration` (±0.1s) and there is an audio stream.
2. Pull 5-6 frames with ffmpeg into `projects/<slug>/qa/`: 1s in, just before and just after the first drop, the middle, and 1s before the end. Look at them (Read the PNGs). Blank frames, overflowing text, or a drop that doesn't look different from the build-up are bugs. Fix them and re-render.

```bash
mkdir -p projects/<slug>/qa && ffmpeg -y -loglevel error -ss <t> -i output/<slug>.mp4 -frames:v 1 projects/<slug>/qa/<t>.png
```

## 7. Report

Tell the user: output path, clip window used (start → end in the song), BPM/key, the archetype and concept in one sentence, and how the drop is handled. Don't open the video for them; they'll open it themselves.
