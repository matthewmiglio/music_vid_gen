# music_vid_gen

Turn a song into a beat-synced music video with Claude Code + [HyperFrames](https://hyperframes.heygen.com).

```
/generate-music-video E:/my_files/my_music/luvme.wav          # 30s clip (default)
/generate-music-video E:/my_files/my_music/luvme.wav 1:00     # 60s clip
/generate-music-video E:/my_files/my_music/luvme.wav whole    # entire song
```

What the skill does:

1. **Measures the song** with `scripts/analyze_song.py`: tempo, beat grid, bars, key, chords, loudness, stereo, timbre, sections, drops, breakdowns, accent hits. It picks the best clip window (highest energy, preferring one that contains a drop, starting on a bar line) and writes per-frame bass-to-treble levels for the animation.
2. **Listens to the song** with the `/analyze-audio` skill (Gemini) for genre, mood, vocals and visual ideas.
3. **Picks a visual concept** and writes it to the project's `DESIGN.md`: palette, fonts, and a timeline with scene cuts on bar lines and the big change on the drop.
4. **Builds a HyperFrames project** in `projects/<song>-v<N>/`, lints and checks it, then **renders** to `output/<song>-v<N>.mp4` and spot-checks frames.

Each run creates a new project, so running the same song twice gives two different videos.

## Layout

```
.claude/skills/generate-music-video/SKILL.md   the project-level skill
scripts/analyze_song.py                        song analysis tool
projects/                                      one HyperFrames project per video
output/                                        rendered MP4s (git-ignored)
```

## Analyzer on its own

```bash
python scripts/analyze_song.py song.wav                          # print a summary
python scripts/analyze_song.py song.wav --length whole -o out/   # + analysis.json, song-data.js, audio.wav
python scripts/analyze_song.py song.wav --length 45 --start 1:12 -o out/
```

## Requirements

- Python 3.10+ with `pip install -r requirements.txt`
- ffmpeg on PATH
- Node 22+ (HyperFrames runs through `npx hyperframes`)
- The `/analyze-audio` skill with a Gemini API key (optional; skip it and the concept comes from the numbers alone)

Song audio (`projects/*/audio.wav`) and rendered videos (`output/`) are git-ignored.
