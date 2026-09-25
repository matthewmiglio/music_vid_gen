#!/usr/bin/env python
"""Analyze a song for music-video generation.

Pulls tempo, beat grid, downbeats, key, chords, loudness, stereo image,
spectral character, sections, drops/breakdowns and accent hits, picks the
best clip window, trims the clip audio, and writes per-frame audio data
that a HyperFrames composition can load synchronously.

Usage:
    python scripts/analyze_song.py song.wav                      # 30s clip, print summary only
    python scripts/analyze_song.py song.wav --length whole -o projects/x
    python scripts/analyze_song.py song.wav --length 1:00 --start 0:42 -o projects/x

Outputs (with -o DIR):
    DIR/analysis.json   full song + clip analysis (song-level times are absolute)
    DIR/song-data.js    window.SONG (clip-relative events) + window.AUDIO_DATA (per-frame bands)
    DIR/audio.wav       the trimmed clip audio (fades applied)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# librosa's numba JIT cache defaults to its own install dir; under Program Files that is
# read-only and numba retries tempfile creation for minutes. Point it somewhere writable.
os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "numba_cache"))

import librosa
import numpy as np

SR = 22050
HOP = 512
FPS = 30
N_BANDS = 16
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Kessler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
BALANCE_BANDS = {"sub": (20, 60), "bass": (60, 250), "low_mid": (250, 500),
                 "mid": (500, 2000), "high_mid": (2000, 6000), "high": (6000, 11025)}


def parse_time(s):
    """'30', '30s', '1:30', '90.5' -> seconds."""
    s = str(s).strip().lower().rstrip("s")
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + float(sec)
    return float(s)


def r(x, n=3):
    return round(float(x), n)


def norm(x, pct=99):
    top = np.percentile(x, pct)
    return np.clip(x / top, 0, 1) if top > 0 else np.zeros_like(x)


def ebur128(path):
    """Integrated loudness (LUFS), loudness range (LU) and true peak via ffmpeg."""
    try:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
                              "-af", "ebur128=peak=true", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=300).stderr
        summary = err[err.rfind("Summary:"):]
        grab = lambda k: float(re.search(k + r":\s+(-?[\d.]+)", summary).group(1))
        return {"integrated_lufs": grab("I"), "loudness_range_lu": grab("LRA"), "true_peak_dbfs": grab("Peak")}
    except Exception as e:  # ffmpeg missing or odd output: the rest of the analysis still works
        return {"error": str(e)}


def estimate_key(chroma_mean):
    scores = []
    for i in range(12):
        scores.append((np.corrcoef(np.roll(MAJOR, i), chroma_mean)[0, 1], KEYS[i], "major"))
        scores.append((np.corrcoef(np.roll(MINOR, i), chroma_mean)[0, 1], KEYS[i], "minor"))
    scores.sort(reverse=True)
    best, second = scores[0], scores[1]
    return {"key": f"{best[1]} {best[2]}", "confidence": r(best[0] - second[0]),
            "runner_up": f"{second[1]} {second[2]}"}


def chord_templates():
    names, temps = [], []
    for i in range(12):
        for quality, iv in (("", (0, 4, 7)), ("m", (0, 3, 7))):
            t = np.zeros(12)
            t[[(i + k) % 12 for k in iv]] = 1
            names.append(KEYS[i] + quality)
            temps.append(t / np.linalg.norm(t))
    return names, np.array(temps)


def estimate_chords(chroma_beats, downbeat_idx, beat_times):
    """One triad guess per bar. Rough: good for mood, not for transcription."""
    names, temps = chord_templates()
    bars = []
    for j, b in enumerate(downbeat_idx):
        end = downbeat_idx[j + 1] if j + 1 < len(downbeat_idx) else b + 4
        c = chroma_beats[:, b + 1:end + 1].mean(axis=1)  # +1: sync column 0 is pre-first-beat
        if np.linalg.norm(c) == 0:
            continue
        sims = temps @ (c / np.linalg.norm(c))
        bars.append((r(beat_times[b], 2), names[int(sims.argmax())] if sims.max() > 0.55 else "N"))
    progression = [bars[0]] if bars else []
    for t, ch in bars[1:]:
        if ch != progression[-1][1]:
            progression.append((t, ch))
    counts = {}
    for _, ch in bars:
        counts[ch] = counts.get(ch, 0) + 1
    common = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
    return {"per_bar": [{"t": t, "chord": ch} for t, ch in bars],
            "changes": [{"t": t, "chord": ch} for t, ch in progression],
            "most_common": [{"chord": ch, "bars": n} for ch, n in common]}


def band_edges(n, lo=30.0, hi=11000.0):
    return np.geomspace(lo, hi, n + 1)


def analyze(path, length_arg="30", start_arg=None):
    path = Path(path)
    y_st, _ = librosa.load(path, sr=SR, mono=False)
    if y_st.ndim == 1:
        y_st = np.vstack([y_st, y_st])
    y = librosa.to_mono(y_st)
    duration = len(y) / SR

    # --- rhythm -----------------------------------------------------------
    onset_env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=SR, hop_length=HOP)
    tempo = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=SR, hop_length=HOP)
    ibi = np.diff(beat_times)
    beat_regularity = r(1 - np.std(ibi) / np.mean(ibi)) if len(ibi) > 1 else 0

    # downbeat phase: kick/bass lands hardest on beat 1 in most pop/trap/edm
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    low = S[(freqs >= 30) & (freqs < 150)].sum(axis=0)
    low_onset = np.maximum(0, np.diff(low, prepend=low[0]))
    bf = np.clip(beat_frames, 0, len(low_onset) - 1)
    phase = int(np.argmax([low_onset[bf[p::4]].mean() if len(bf[p::4]) else 0 for p in range(4)]))
    downbeat_idx = list(range(phase, len(beat_times), 4))
    downbeats = beat_times[downbeat_idx]

    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=SR, hop_length=HOP)
    onset_times = librosa.frames_to_time(onset_frames, sr=SR, hop_length=HOP)
    strength = onset_env[onset_frames] if len(onset_frames) else np.array([])
    accent_mask = strength >= np.percentile(strength, 92) if len(strength) else []
    accents = [{"t": r(t, 2), "strength": r(s / onset_env.max(), 2)}
               for t, s in zip(onset_times[accent_mask], strength[accent_mask])]

    # --- loudness / energy ------------------------------------------------
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    rms_n = norm(rms)
    low_n = norm(low)
    energy = 0.6 * rms_n + 0.4 * low_n[: len(rms_n)]
    frame_t = librosa.frames_to_time(np.arange(len(energy)), sr=SR, hop_length=HOP)
    per_sec = [r(energy[(frame_t >= s) & (frame_t < s + 1)].mean(), 2) for s in range(int(np.ceil(duration)))]
    rms_db = 20 * np.log10(rms + 1e-9)
    _, (trim_start, trim_end) = librosa.effects.trim(y, top_db=45)

    # --- tonal ------------------------------------------------------------
    y_harm, y_perc = librosa.effects.hpss(y)
    h_e, p_e = np.sum(y_harm ** 2), np.sum(y_perc ** 2)
    chroma = librosa.feature.chroma_cqt(y=y_harm, sr=SR, hop_length=HOP)
    key = estimate_key(chroma.mean(axis=1))
    chroma_beats = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
    chords = estimate_chords(chroma_beats, downbeat_idx, beat_times)
    pitch_class_profile = {KEYS[i]: r(v, 2) for i, v in enumerate(chroma.mean(axis=1) / chroma.mean(axis=1).max())}

    # --- timbre / spectrum ------------------------------------------------
    centroid = librosa.feature.spectral_centroid(S=S, sr=SR)[0]
    power = S ** 2
    total = power.sum()
    balance = {k: r(power[(freqs >= lo) & (freqs < hi)].sum() / total * 100, 1)
               for k, (lo, hi) in BALANCE_BANDS.items()}
    L, R = y_st[0], y_st[1]
    mid, side = (L + R) / 2, (L - R) / 2
    stereo = {"lr_correlation": r(np.corrcoef(L, R)[0, 1]) if np.std(L) and np.std(R) else 1.0,
              "side_to_mid_ratio": r(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-9))}

    # --- structure --------------------------------------------------------
    mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP)
    feat = np.vstack([librosa.util.normalize(chroma, axis=0), librosa.util.normalize(mfcc, axis=1)])
    feat_b = librosa.util.sync(feat, beat_frames, aggregate=np.median)
    k = int(np.clip(round(duration / 20), 3, 10))
    bounds_col = librosa.segment.agglomerative(feat_b, k)
    col_time = lambda c: 0.0 if c == 0 else float(beat_times[min(c - 1, len(beat_times) - 1)])
    bounds = sorted({col_time(c) for c in bounds_col} | {0.0})
    sec_edges = bounds + [duration]
    seg_energy = [energy[(frame_t >= a) & (frame_t < b)].mean() for a, b in zip(sec_edges[:-1], sec_edges[1:])]
    q1, q2 = np.percentile(seg_energy, [33, 66])
    sections = []
    for (a, b), e in zip(zip(sec_edges[:-1], sec_edges[1:]), seg_energy):
        m = (frame_t >= a) & (frame_t < b)
        sections.append({"start": r(a, 2), "end": r(b, 2), "energy": r(e, 2),
                         "level": "low" if e < q1 else "mid" if e < q2 else "high",
                         "brightness_hz": int(centroid[m[: len(centroid)]].mean())})

    # --- drops and breakdowns (energy jumps at downbeats) ------------------
    beat_e = np.array([energy[(frame_t >= a) & (frame_t < b)].mean() if b > a else 0
                       for a, b in zip(beat_times, np.append(beat_times[1:], duration))])
    jumps = []
    for i in downbeat_idx:
        if i < 8 or i + 8 > len(beat_e):
            continue
        pre, post = beat_e[i - 8:i].mean(), beat_e[i:i + 8].mean()
        jumps.append((i, post - pre, post))
    def pick(cands, sign):
        chosen = []
        for i, d, post in sorted(cands, key=lambda c: -sign * c[1]):
            if sign * d < 0.12 or any(abs(i - j) < 16 for j, *_ in chosen):
                continue
            chosen.append((i, d, post))
        return sorted(chosen[:6])
    high_e = np.percentile(beat_e, 60)
    drops = [{"t": r(beat_times[i], 2), "jump": r(d, 2), "energy_after": r(p, 2)}
             for i, d, p in pick([c for c in jumps if c[2] >= high_e], 1)]
    breakdowns = [{"t": r(beat_times[i], 2), "fall": r(-d, 2)} for i, d, _ in pick(jumps, -1)]

    # --- clip window --------------------------------------------------------
    whole = str(length_arg).lower() in ("whole", "whole song", "full", "all")
    clip_len = duration if whole else min(parse_time(length_arg), duration)
    if start_arg is not None:
        clip_start, reason = min(parse_time(start_arg), max(0, duration - clip_len)), "user override"
    elif clip_len >= duration - 0.5:
        clip_start, clip_len, reason = 0.0, duration, "whole song"
    else:
        es = np.array(per_sec)
        best = None
        for t in downbeats:
            if t + clip_len > duration:
                break
            a, b = int(t), int(t + clip_len)
            score = es[a:b].mean()
            in_win = [d["jump"] for d in drops if t + 0.2 * clip_len <= d["t"] <= t + 0.6 * clip_len]
            score += 0.8 * max(in_win, default=0)
            score += 0.05 if any(abs(t - s["start"]) < 0.6 for s in sections) else 0
            if best is None or score > best[0]:
                best = (score, float(t), bool(in_win))
        if best is None:
            best = (0, 0.0, False)
        clip_start = best[1]
        reason = "highest energy window" + (" containing a drop" if best[2] else "")
    clip_end = clip_start + clip_len

    rel = lambda t: r(t - clip_start, 3)
    inside = lambda t: clip_start - 0.01 <= t < clip_end  # events are rounded to 10ms
    clip = {
        "start": r(clip_start, 3), "end": r(clip_end, 3), "duration": r(clip_len, 3), "reason": reason,
        "beats": [rel(t) for t in beat_times if inside(t)],
        "downbeats": [rel(t) for t in downbeats if inside(t)],
        "drops": [{**d, "t": max(0, rel(d["t"]))} for d in drops if inside(d["t"])],
        "breakdowns": [{**d, "t": max(0, rel(d["t"]))} for d in breakdowns if inside(d["t"])],
        "accents": [{**a, "t": rel(a["t"])} for a in accents if inside(a["t"])],
        "sections": [{**s, "start": max(0, rel(s["start"])), "end": min(r(clip_len, 3), rel(s["end"]))}
                     for s in sections if s["end"] > clip_start and s["start"] < clip_end],
        "chord_changes": [{**c, "t": rel(c["t"])} for c in chords["changes"] if inside(c["t"])],
        "energy_per_second": per_sec[int(clip_start): int(np.ceil(clip_end))],
    }

    analysis = {
        "file": str(path), "name": path.stem,
        "duration": r(duration, 2), "sample_rate": librosa.get_samplerate(path),
        "tempo": {"bpm": r(tempo, 1), "half_time": r(tempo / 2, 1), "double_time": r(tempo * 2, 1),
                  "beat_regularity": beat_regularity, "beats_per_bar_assumed": 4,
                  "bar_seconds": r(240 / tempo, 3) if tempo else None},
        "beats": [r(t, 3) for t in beat_times],
        "downbeats": [r(t, 3) for t in downbeats],
        "onsets_per_second": r(len(onset_times) / duration, 2),
        "accents": accents,
        "key": key, "pitch_class_profile": pitch_class_profile, "chords": chords,
        "loudness": {**ebur128(path), "rms_dbfs_mean": r(rms_db.mean(), 1),
                     "rms_dbfs_p95": r(np.percentile(rms_db, 95), 1),
                     "crest_factor_db": r(20 * np.log10(np.abs(y).max() / (np.sqrt(np.mean(y ** 2)) + 1e-9)), 1),
                     "leading_silence_s": r(trim_start / SR, 2), "trailing_silence_s": r(duration - trim_end / SR, 2)},
        "timbre": {"spectral_centroid_hz": int(centroid.mean()),
                   "spectral_rolloff_hz": int(librosa.feature.spectral_rolloff(S=S, sr=SR)[0].mean()),
                   "spectral_flatness": r(librosa.feature.spectral_flatness(S=S)[0].mean(), 4),
                   "zero_crossing_rate": r(librosa.feature.zero_crossing_rate(y, hop_length=HOP)[0].mean(), 4),
                   "harmonic_pct": r(h_e / (h_e + p_e) * 100, 1), "percussive_pct": r(p_e / (h_e + p_e) * 100, 1),
                   "band_balance_pct": balance},
        "stereo": stereo,
        "energy_per_second": per_sec,
        "sections": sections, "drops": drops, "breakdowns": breakdowns,
        "clip": clip,
    }
    return analysis, y


def frame_data(y, clip_start, clip_len):
    """Per-frame RMS + log-spaced band amplitudes, each normalized over the whole track."""
    hop = SR // FPS
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=hop)) ** 2
    freqs = librosa.fft_frequencies(sr=SR, n_fft=4096)
    edges = band_edges(N_BANDS)
    bands = np.array([S[(freqs >= lo) & (freqs < hi)].sum(axis=0) for lo, hi in zip(edges[:-1], edges[1:])])
    bands = np.sqrt(bands)
    bands = np.array([norm(b, 98) for b in bands])
    rms = norm(librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0], 98)
    f0, n = int(round(clip_start * FPS)), int(round(clip_len * FPS))
    frames = []
    for f in range(f0, f0 + n):
        f = min(f, bands.shape[1] - 1)
        frames.append({"rms": round(float(rms[min(f, len(rms) - 1)]), 2),
                       "bands": [round(float(v), 2) for v in bands[:, f]]})
    return {"fps": FPS, "totalFrames": n, "bandEdgesHz": [int(e) for e in edges], "frames": frames}


def write_clip_audio(src, dst, start, length, full_duration):
    af = []
    if start > 0.05:
        af.append("afade=t=in:st=0:d=0.25")
    if start + length < full_duration - 0.05:
        af.append(f"afade=t=out:st={max(0, length - 1.5):.3f}:d=1.5")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
           "-i", str(src)] + (["-af", ",".join(af)] if af else []) + ["-c:a", "pcm_s16le", str(dst)]
    subprocess.run(cmd, check=True)


def summary(a):
    c = a["clip"]
    lines = [
        f"{a['name']}  |  {a['duration']}s  |  {a['tempo']['bpm']} BPM (half {a['tempo']['half_time']}, "
        f"double {a['tempo']['double_time']}; regularity {a['tempo']['beat_regularity']})",
        f"key {a['key']['key']} (confidence {a['key']['confidence']}, runner-up {a['key']['runner_up']})",
        f"chords (most common): " + ", ".join(f"{x['chord']}x{x['bars']}" for x in a["chords"]["most_common"]),
        f"loudness {a['loudness'].get('integrated_lufs')} LUFS, range {a['loudness'].get('loudness_range_lu')} LU, "
        f"crest {a['loudness']['crest_factor_db']} dB",
        f"timbre centroid {a['timbre']['spectral_centroid_hz']} Hz, harmonic {a['timbre']['harmonic_pct']}% / "
        f"percussive {a['timbre']['percussive_pct']}%, onsets/s {a['onsets_per_second']}",
        "band balance %: " + ", ".join(f"{k} {v}" for k, v in a["timbre"]["band_balance_pct"].items()),
        f"stereo corr {a['stereo']['lr_correlation']}, side/mid {a['stereo']['side_to_mid_ratio']}",
        "sections: " + " | ".join(f"{s['start']}-{s['end']} {s['level']}" for s in a["sections"]),
        "drops: " + (", ".join(f"{d['t']}s (+{d['jump']})" for d in a["drops"]) or "none detected"),
        "breakdowns: " + (", ".join(f"{d['t']}s (-{d['fall']})" for d in a["breakdowns"]) or "none"),
        f"CLIP {c['start']}s -> {c['end']}s ({c['duration']}s, {c['reason']}): {len(c['beats'])} beats, "
        f"{len(c['downbeats'])} bars, drops at {[d['t'] for d in c['drops']]}, "
        f"section changes at {[s['start'] for s in c['sections']]}",
        "clip energy/s: " + " ".join(f"{e:.1f}" for e in c["energy_per_second"]),
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song")
    ap.add_argument("--length", default="30", help="seconds, M:SS, or 'whole' (default 30)")
    ap.add_argument("--start", help="force clip start (seconds or M:SS) instead of auto-picking")
    ap.add_argument("-o", "--out", help="output directory for analysis.json, song-data.js, audio.wav")
    args = ap.parse_args()

    a, y = analyze(args.song, args.length, args.start)
    print(summary(a))
    if not args.out:
        return
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(a, indent=1))
    c = a["clip"]
    song = {k: c[k] for k in ("duration", "beats", "downbeats", "drops", "breakdowns", "accents",
                              "sections", "chord_changes", "energy_per_second")}
    song.update(bpm=a["tempo"]["bpm"], bar_seconds=a["tempo"]["bar_seconds"], key=a["key"]["key"],
                title=a["name"], source_start=c["start"], source_end=c["end"])
    audio = frame_data(y, c["start"], c["duration"])
    (out / "song-data.js").write_text(
        "// generated by scripts/analyze_song.py; times are seconds from the start of the clip\n"
        f"window.SONG = {json.dumps(song, separators=(',', ':'))};\n"
        f"window.AUDIO_DATA = {json.dumps(audio, separators=(',', ':'))};\n")
    write_clip_audio(args.song, out / "audio.wav", c["start"], c["duration"], a["duration"])
    print(f"\nwrote {out / 'analysis.json'}, {out / 'song-data.js'}, {out / 'audio.wav'}")


if __name__ == "__main__":
    sys.exit(main())
