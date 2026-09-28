# Style: psychedelic

The pinned default style. A psychedelic trip that starts from real subjects, drawn entirely in code, where subjects morph into each other and drift into abstraction.

**Benchmark:** `trappin-in-japan-1-v4`. Its drawing was detailed and stylized in every frame (Mount Fuji above a sea of clouds, a goshawk rigged from moving parts, Sakurajima erupting with volcanic lightning, a bamboo grove in a gale), with a heavy WebGL pass on top: Fuji's snowcap folding into a kaleidoscope, the hawk boiling into the ash plume, lightning splitting into bamboo stalks, and an ending in stained-glass symmetry. The user's verdict on the version before it: "very cool. I like how intriguing each one is. Very detailed and stylized per frame."

## The look

Every video is a **psychedelic sequence of 5-10 second scenes that starts from real-world subjects**: an ocean swell breaking, a bear rearing up and roaring, a volcano erupting, a goshawk striking, whales breaching, a thunderstorm, a wolf pack in snow, the northern lights. The real subject is the **starting point**. From there the video should feel like a trip: subjects melt, mutate and morph into each other, and the frame is allowed to drift into full abstract psychedelia before a new subject comes into focus. **Psychedelic comes first; realism is optional.**

- **Morphing is the core device.** Animals and objects turn into other animals and objects on screen: a heron's wings stretch into a stag's antlers, a whale's tail unfurls into a wave that becomes a flock of birds, a volcano's ash plume curls into a dragon or wolf. Use morphs for most scene changes instead of plain crossfades (shape interpolation between paths, pixels melting through a displacement field, a kaleidoscope folding one subject into the next, or a silhouette filling with the next creature). Plan the morph chain in DESIGN.md.
- **Heavy psychedelic treatment the whole way through**, not only on the drop. Stack two to four treatments, driven by the audio: liquid warping, kaleidoscope and mirror symmetry, chromatic RGB split, hue cycling and gradient maps, echo and feedback trails, solarizing, fractal zooms, breathing and pulsing edges, moiré and interference shimmer, and melting drips. Start at a strong level and go wild on the drop. This overrides the HyperFrames guide's "no rainbow color cycling" rule.
- **Abstract psychedelic moments are welcome**, such as a kaleidoscope bloom, a fractal tunnel, or liquid color fields between subjects. What's still out is *flat* geometry with no trip in it: plain op-art patterns, Swiss-style shapes, and text-only frames.
- **Detailed and stylized in every frame.** Dense detail, a strong stylized look, and several things happening at once. The looks that fit are psychedelic poster art, 70s album covers, visionary art (Alex Grey-style glowing anatomy), ukiyo-e crossed with neon, and stained glass. Not flat clip art, not cute, and not a plain nature illustration. Thin neon outline creatures read weaker than solid, detailed ones.
- **Drawn in code, never footage.** Build everything from layered SVG, canvas 2D and/or Three.js/WebGL (the `hyperframes-animation` skill has a Three.js adapter). No stock video, no photos, no AI-generated images.
- **Heavy animation inside every scene**, not only camera moves: jaws open, wings beat, waves break, plumes boil. Rig creatures from separate parts (jaw, head, wings, legs) that rotate around their hinges. Something in the frame is always moving.
- **Scene cuts and morphs land on downbeats.** About 3-6 scenes for a 30-second clip, more for a whole song. **Put the most spectacular moment on the first drop**: the biggest morph, the roar, the eruption.

## DESIGN.md additions

- `## Concept` covers the **morph chain** (what turns into what, and when) and the treatments.
- `## Timeline` gives each scene's morph into the next and a psychedelic level (1-3; never 0). Breakdowns drift into slower, dreamier abstraction rather than going plain.

## Technique

- **Start the effects pass from `templates/psychedelic-post.js`.** Copy it into the project. It is a WebGL2 shader that runs fine without a GPU. Draw each scene to its own canvas, then every frame call `POST.render(sceneCanvasA, sceneCanvasB, params)` onto one full-frame output canvas (`POST.init(canvas)` once). It covers mirror symmetry, kaleidoscope, fractal zoom, liquid warp, morphs between two scenes (`mixT` + `mode`: noise melt, burn-through, upward smoke melt), RGB split, echo trails, neon edges, hue cycle, gradient map, solarize, grain and vignette. Read the uniform list at the top for parameter names. Every parameter must be computed from time and audio data only. Faint SVG filters are too weak to read as psychedelic.
- Keep the kaleidoscope and fractal-zoom strength moderate while a creature is on screen, because at full strength they turn it to mush. For "many copies of the animal", draw rotated copies in 2D instead.
- Solarize or inversion combined with hue cycling easily washes frames out into muddy pastels, so keep the darks dark.
- Keep the hero creature big and bright enough to survive the effects; in the benchmark video, the goshawk nearly disappeared into mirrored trees.
