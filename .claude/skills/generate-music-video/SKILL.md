---
name: generate-music-video
description: Turn a song file into a rendered, beat-synced HyperFrames music video made of code-drawn real-world scenes (oceans, cities, animals) with psychedelic effects on top. Analyzes the song (scripts/analyze_song.py + /analyze-audio), picks scenes that fit it, builds a new project in projects/, renders it to output/. Use when the user runs /generate-music-video <song> [length], or asks to make a music video / visualizer for a song.
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
python "C:/Users/matt/.claude/skills/analyze-audio/analyze_audio.py" projects/<slug>/audio.wav --question "Describe this track for a music-video director: genre and subgenre, mood and emotional arc, vocal presence and delivery (and any lyrics you can make out), standout sounds, how the energy moves across the clip, and the colors, textures, weather, landscapes, animals and natural or urban forces it evokes (e.g. a storm, a predator, a flood, a city waking up). Skip driving, roads and nightlife. Be concrete." > projects/<slug>/gemini-analysis.md
```

(Only stdout goes to the file; token usage prints on stderr.) Treat its key, chord and plugin claims as guesses (the numbers from step 2 win). Trust it on mood, genre and imagery. Ignore any late-night driving, wet asphalt or neon it suggests anyway; those lead to the banned night-drive look.

## 4. Choose the concept

### 4a. The look: real scenes, drawn in code, with psychedelic effects on top

Every video is a sequence of **real-world scenes**, each lasting **5-10 seconds**: an ocean swell breaking, a city timelapse from day to night, a bear rearing up and roaring, a thunderstorm over plains, a wolf pack running through snow, a volcano erupting, whales breaching, a jet going supersonic, a forest fire, a stampede, a rocket launch, a jellyfish bloom, a desert sandstorm, the northern lights over mountains, a crowd at a stadium. The viewer should recognize what they're looking at right away.

- **Drawn in code, never footage.** Build each scene from layered SVG, canvas 2D and/or Three.js/WebGL (the `hyperframes-animation` skill has a Three.js adapter). No stock video, no photos, no AI-generated images.
- **Heavy animation inside the scene**, not only camera moves. The waves roll and break, clouds race, city lights switch on window by window, the bear's jaw opens, its head throws back, its breath fogs, and the ground shakes. Rig creatures from separate SVG parts (jaw, head, forelegs) that rotate around their hinges. Something in the frame is always moving.
- **Style: cinematic illustration.** Aim for a high-end animated film or motion-design reel: depth from 3-5 parallax layers, atmosphere (fog, god rays, spray, dust, rain or snow as part of the scene), dramatic lighting, and rich gradients with grain. Not flat clip art, and not cute.
- **Psychedelic effects on top of the scenes.** Layer one or two treatments over the real scene, driven by the audio: liquid warping (SVG `feTurbulence` + `feDisplacementMap`), kaleidoscope mirroring, chromatic RGB split, hue-shifting color maps, echo trails, solarizing, or breathing edge warps. Keep them subtle during the build-up and let them take over on the drop, so the scene melts but stays recognizable. This overrides the HyperFrames guide's "no rainbow color cycling" rule, but only as a treatment over a scene, never on its own.
- **No frames that are purely geometric or abstract.** Every frame has a real subject in it. Geometric pattern backgrounds, op-art, floating shapes and text-only frames are out. (A title card over a live scene is fine.)
- **Scene cuts land on downbeats**, with a transition between every scene. Count the scenes to fit: about 3-6 for a 30-second clip, more for a whole song. **Put the most spectacular moment on the first drop**, like the roar, the wave breaking or the eruption.

### 4b. Vary the scenes across the library

1. Run `grep -h "^Scenes:" projects/*/DESIGN.md` to see which subjects other videos already used, across **all** songs.
2. Don't reuse a subject from any other project (so no second bear, no second ocean). Also vary the palette and the time of day from the most recent project (`ls -t projects | head -2`, then read its DESIGN.md).
3. Choose subjects whose energy matches the song: a slow, heavy, dark track suggests a storm rolling in or a bear waking in a cave, while fast bright energy suggests a stampede or a city at rush hour. Use Gemini's mood and imagery notes.

### 4c. Rules for every concept

- **Don't base the concept on the song title.** File names are working titles and are usually meaningless or misleading. Only use the title when it names something concrete and visual, such as a place ("japan" can suggest a Tokyo skyline or Mount Fuji). Titles like "luvme", "safe2" or "clams" must not drive the imagery: no hearts for a song called "luv", and no clams for "clams". Putting the title on screen as text is fine.
- **No childish or cute looks.** Avoid cartoon mascots, big-eyed cute animals, balloon or inflatable shapes, bouncy squash-and-stretch toys, candy or pastel-toy palettes and bubble fonts. The bear should be terrifying, not a teddy. Aim for album art, a film title sequence or a design-studio reel: stylish, confident and adult.
- **No night-drive clichés:** no first-person trip down a road or tunnel at night past rain and neon signs.

### 4d. Write DESIGN.md

Write `projects/<slug>/DESIGN.md` before any HTML (the HyperFrames skill requires it). The first line must be `Scenes: <comma-separated subjects>` (e.g. `Scenes: grizzly bear, glacier calving, aurora`). If other videos are being made at the same time, write this line first, then run the grep from 4b again before building, and change subjects if there's a clash.

- `## Concept`: one paragraph on the scene sequence and the psychedelic treatment, and why they fit how the song **sounds and feels** (Gemini's notes, tempo, energy, key).
- `## Colors`: 3-5 hex values with roles, taken from the mood.
- `## Typography`: 1-2 families for the title and any text. Prefer these fonts, which work with no setup (some are built in; the rest are fetched from Google Fonts automatically at check and render time): Montserrat, Oswald, League Gothic, Archivo Black, Space Mono, IBM Plex Mono, JetBrains Mono, Source Code Pro, Noto Sans JP (see `hyperframes-creative/references/typography.md`). For anything else, copy a `.ttf` into `projects/<slug>/fonts/` and declare it with `@font-face`, or lint fails with `font_family_without_font_face`.
- `## Timeline`: a table of scenes, each with start and end time (on downbeats), the subject, what moves in it, and the psychedelic level (0-3). The biggest moment lands on the **first drop** (or the highest-energy section start when there's no drop). Breakdowns get calmer shots with less treatment.
- `## Audio mapping`: which signal drives which property (e.g. bass `bands[0-1]` → ground shake and displacement strength, `rms` → treatment intensity, `accents` → lightning or a camera jolt, `beats` → wave pulses, `chord_changes` → hue shift).
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
- Audio-reactive bans (from the HyperFrames guide): no equalizer bars, spectrum analyzers, waveforms, music-note clip art, particle fields that aren't part of the scene, white strobes on every beat, or abstract pulsing orbs. Audio drives *behavior*; the scene decides *what's on screen*.
- Text: the song title (from the filename, cleaned up) belongs somewhere, usually the intro. Keep text pulses to 3-6% scale; backgrounds can swing 10-30%.
- Visuals must be drawn in the page with CSS, SVG, canvas or WebGL. No footage, photos or generated images. A registry block (`hyperframes-registry` skill) is fine for an effect such as a shader transition or grain.
- Build one scene per `<div class="clip">` (or per sub-composition in `compositions/` if `index.html` gets unwieldy). Put the psychedelic layer on a wrapper around the scene (a filter or overlay), so it can ramp up and down without touching the scene's own animation.
- Deterministic randomness: a seeded PRNG (mulberry32), never `Math.random()`.
- A single large `index.html` triggers the lint warning `composition_file_too_large`. It's harmless and can be ignored.
- `energy_per_second` is more detailed than `sections`. Check it for silence (values near 0), such as a song that ends early, so you don't animate over nothing.

## 6. Check, preview, render, verify

```bash
npx hyperframes lint projects/<slug>
npx hyperframes check projects/<slug> --no-browser-gpu
npx hyperframes snapshot projects/<slug> --at 1,<pre-drop>,<post-drop>,<mid>,<end-1> --no-end --describe false --no-browser-gpu
```

Fix every lint error and every layout and contrast issue from `check`, including contrast warnings. Then look at the snapshot PNGs in `projects/<slug>/snapshots/`, which is much cheaper than a render. Fix anything wrong and snapshot again. When the frames look right, render:

```bash
mkdir -p output
npx hyperframes render projects/<slug> -o output/<slug>.mp4 --quality standard --no-browser-gpu --crf 20
```

**CPU only:** always pass `--no-browser-gpu` to `check`, `snapshot` and `render` (the user wants the GPU left alone), and never pass `--gpu`. `--crf 20` keeps a 30s video around 15-30 MB instead of ~180 MB. If several renders run at once, add `--workers 3` to each. Then verify the actual video:

1. `ffprobe` the MP4: duration matches `SONG.duration` (±0.1s) and there is an audio stream.
2. Pull 5-6 frames with ffmpeg into `projects/<slug>/qa/`: 1s in, just before and just after the first drop, the middle, and 1s before the end. Look at them (Read the PNGs). Blank frames, overflowing text, or a drop that doesn't look different from the build-up are bugs. Fix them and re-render.

```bash
mkdir -p projects/<slug>/qa && ffmpeg -y -loglevel error -ss <t> -i output/<slug>.mp4 -frames:v 1 projects/<slug>/qa/<t>.png
```

## 7. Report

Tell the user: output path, clip window used (start → end in the song), BPM/key, the scene list, the psychedelic treatment, and what happens on the drop. Don't open the video for them; they'll open it themselves.
