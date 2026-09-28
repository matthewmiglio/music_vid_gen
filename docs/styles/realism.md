# Style: realism

As close to real filmed footage as code can get: a nature documentary or a film's aerial second unit, cut to the music. No psychedelic effects, no illustration, no stylized outlines. The viewer should briefly wonder whether it was filmed.

## What code can make look real (and what it can't)

Procedural and raymarched rendering gets close to photographic for **natural phenomena**, so build videos out of these:

- open ocean, storm swell, waves breaking, spray, foam, sun glitter
- skies and volumetric clouds, sunsets, a storm front rolling in, lightning inside clouds
- mountain ranges and terrain from the air, snowfields, glaciers, desert dunes, canyons
- lava, an eruption plume, glowing fissures
- aurora, a starfield and Milky Way, planet Earth from orbit with the terminator line
- fog in a valley, rain, snow, dust storms, sun rays through haze

It **can't** make close-up animals, people, faces or detailed cities look real. Keep living things **small, distant, backlit or partly hidden**: a flock of birds far off, a whale's back and blow seen through spray, a lone figure silhouetted on a ridge. Pick the song's subjects from the first list; don't build the video around a close-up creature.

## The look

- **Photographic lighting.** One physically plausible sun or sky light, soft shadows, atmospheric scattering (distant things fade blue and hazy), and realistic sky color for the time of day. Render in linear color with HDR values, then tonemap with an ACES-style filmic curve. Never flat saturated colors.
- **A real camera.** Camera moves that a drone, helicopter or telephoto lens would make: slow push-ins, orbits, low passes over water, locked-off wides. Add subtle handheld or drone drift, depth of field where it makes sense, lens effects (gentle bloom on highlights, faint lens dirt, slight vignette, very slight chromatic aberration at the edges), fine film grain, and motion blur on fast moves.
- **A color grade** that matches the song's mood, like a film grade: teal and orange, bleach bypass, cold Nordic blue, golden hour. The grade is the only "style" allowed.
- **Scene length 5-10s**, edited like a film trailer: cuts and match cuts on downbeats, a few dips to black or white on big moments. Hard cuts on the beat are fine in this style (they count as the transition).
- **Beat sync is motivated, not decorative.** The music should seem to cause real events: lightning on accents, a wave slamming the rocks on the downbeat, a camera cut on each bar, the sun breaking through the clouds on the drop, a thunder-shake of the camera on the kick. Nothing pulses, glows or warps just because of the beat.
- **The drop is the biggest real event**: the eruption, the wave hitting, the storm breaking, the lightning strike.
- **Titles** are small and cinematic (thin tracked-out caps or a clean serif, like a documentary title), not graphic-design type.

## Technique

- **Raymarched WebGL2 fragment shaders** are the main tool: signed-distance or heightfield terrain with fBm noise, ray-traced ocean surfaces with Fresnel reflection of the sky, volumetric clouds and smoke via density raymarching with light marching, a physically based sky (Rayleigh and Mie scattering). Three.js is fine where meshes help (for example `Water` and `Sky` from the three.js examples, or a PBR scene).
- **Write the shaders yourself.** Use well-known techniques (Inigo Quilez's articles on terrain, clouds and noise are the reference), but don't paste Shadertoy code: most of it is licensed non-commercial and share-alike, and this repo is public.
- **CC0 assets are allowed in this style** as materials and lighting, not as footage: HDRI skies and PBR textures from Poly Haven (polyhaven.com, all CC0) can be downloaded into the project and sampled in the shader. Note what you used in DESIGN.md.
- **Render cost on CPU is the constraint.** Raymarching through SwiftShader (the software renderer used with `--no-browser-gpu`) is slow. Render the shader at a lower internal resolution (for example 1280x720, or 960x540 for heavy clouds) into a canvas the size of the frame, and let the upscale plus grain hide it. Cap raymarch steps (around 64-96 for terrain and ocean, 32-48 density samples for clouds), and snapshot one frame early to measure how long a frame takes before building everything. Budget roughly 1-3 s per frame at most. Snapshot timings run alone; with other renders going at the same time, the real render can be up to 5 times slower per frame. `check` prints "GPU stall due to ReadPixels" warnings under the software renderer; they are harmless.
- **Ground and close foreground give realism away fastest** (smooth texture instead of grass or rock, soft upscaled edges). Keep the camera high, the ground in haze or motion blur, or frame it out; spend detail on the sky, water and weather.
- **Every shot is a different subject or place.** The user found a video that was one storm from five angles repetitive. Treat the 30 seconds as a montage across locations (for example: storm front, then open ocean, then a volcano, then aurora), and also vary the lens (wide, telephoto, aerial, ground level) and the light.
- **Shader gotchas:** inside raymarch loops, sample textures with an explicit mip level 0 (`textureLod(..., 0.0)`), and store heightmaps as 32-bit float, because half-float heights show visible terracing.
- **Everything is a pure function of time and audio data.** No accumulation across frames, since frames are rendered out of order and in parallel. For motion blur, sample time a few times inside the shader instead of blending with the previous frame.
- Don't use the psychedelic effects pass (`templates/psychedelic-post.js`). A small, separate finishing shader for tonemapping, bloom, grain, vignette and a grade is the right amount.

## DESIGN.md additions

- `## Concept` names the real subjects, the time of day and weather, the camera language, and the grade.
- `## Timeline` gives each shot's subject, camera move, the real event that lands on the beat, and the transition.
- `## Realism risks`: which shots are hardest to make believable, and how you'll keep them convincing (distance, fog, backlight, short duration).
