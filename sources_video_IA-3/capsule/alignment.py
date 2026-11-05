"""Find when each paragraph is spoken in the recording, and how wide the mouth opens.

Speech is detected from the loudness; paragraph boundaries are chosen among the pauses by dynamic
programming, preferring pauses close to the position expected from the text length. In duo mode the
two voices alternate and their pitch difference is used as extra evidence.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import Project
from .errors import CapsuleError
from .speakers import Speaker
from .timeline import END_DURATION, END_HOLD, INTRO, Timeline

SAMPLE_RATE = 16000
HOP = 160  # samples per analysis frame (10 ms)
FRAMES_PER_SECOND = SAMPLE_RATE // HOP
MIN_PAUSE_FRAMES = 12  # shorter silences are treated as speech (120 ms)
MIN_SPEECH_FRAMES = 8  # shorter sounds are treated as silence (80 ms)
HIGHER_PITCH_SPEAKER = Speaker.PERSON_2  # duo mode: whose voice is expected to be higher


@dataclass
class Alignment:
    audio_offset: float  # where the recording starts in the video (s)
    lines: list[tuple[float, float]]  # start and end of each line in the video (s)
    envelopes: dict[
        Speaker, np.ndarray
    ]  # mouth opening 0..1 per speaker, FRAMES_PER_SECOND values per second

    def save(self, timing_path: Path, envelope_path: Path) -> None:
        timing_path.parent.mkdir(parents=True, exist_ok=True)
        timing = {"audio_offset": self.audio_offset, "lines": [list(span) for span in self.lines]}
        timing_path.write_text(json.dumps(timing, indent=1))
        envelopes = {speaker.value: np.round(e, 3).tolist() for speaker, e in self.envelopes.items()}
        envelope_path.write_text(json.dumps({"fps": FRAMES_PER_SECOND, **envelopes}))


def load_audio(path: Path) -> np.ndarray:
    """Mono float samples at SAMPLE_RATE, decoded by ffmpeg."""
    if shutil.which("ffmpeg") is None:
        raise CapsuleError("ffmpeg est introuvable : l’installer (voir LISEZMOI.txt)")
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise CapsuleError(f"ffmpeg n'a pas pu lire {path} :\n{result.stderr.decode(errors='replace')}")
    return np.frombuffer(result.stdout, np.float32)


def loudness_db(samples: np.ndarray) -> np.ndarray:
    """RMS level of each 10 ms frame, in dB."""
    n = len(samples) // HOP
    frames = samples[: n * HOP].reshape(n, HOP)
    return 20 * np.log10(np.sqrt((frames**2).mean(1) + 1e-12))


def runs(mask: np.ndarray) -> list[tuple[bool, int, int]]:
    """Maximal runs of equal values: (value, start, end) with end excluded."""
    result, i, n = [], 0, len(mask)
    while i < n:
        j = i
        while j < n and mask[j] == mask[i]:
            j += 1
        result.append((bool(mask[i]), i, j))
        i = j
    return result


def speech_segments(speech: np.ndarray) -> list[tuple[int, int]]:
    """Frame ranges of speech, after closing tiny pauses and dropping tiny blips."""
    speech = speech.copy()
    n = len(speech)
    for is_speech, i, j in runs(speech):
        if not is_speech and j - i < MIN_PAUSE_FRAMES and i > 0 and j < n:
            speech[i:j] = True
    for is_speech, i, j in runs(speech):
        if is_speech and j - i < MIN_SPEECH_FRAMES:
            speech[i:j] = False
    return [(i, j) for is_speech, i, j in runs(speech) if is_speech]


def pitch_track(samples: np.ndarray, n_frames: int) -> np.ndarray:
    """Crude autocorrelation pitch (Hz) per 10 ms frame over a 40 ms window; 0 when unvoiced."""
    f0 = np.zeros(n_frames)
    window = 640
    lag_min, lag_max = SAMPLE_RATE // 400, SAMPLE_RATE // 70
    for i in range(0, n_frames, 2):
        segment = samples[i * HOP : i * HOP + window]
        if len(segment) < window:
            break
        segment = segment - segment.mean()
        if (segment**2).sum() < 1e-6:
            continue
        autocorrelation = np.correlate(segment, segment, "full")[window - 1 :]
        lag = lag_min + np.argmax(autocorrelation[lag_min:lag_max])
        if autocorrelation[lag] / autocorrelation[0] > 0.45:
            f0[i] = f0[min(i + 1, n_frames - 1)] = SAMPLE_RATE / lag
    return f0


def pitch_sides(samples: np.ndarray, segments: list[tuple[int, int]], n_frames: int) -> np.ndarray:
    """For each segment: +1 if it sounds like the higher voice, -1 the lower one, 0 unknown."""
    f0 = pitch_track(samples, n_frames)
    log_pitch = []
    for i, j in segments:
        voiced = f0[i:j][f0[i:j] > 0]
        log_pitch.append(np.median(np.log(voiced)) if len(voiced) > 5 else np.nan)
    log_pitch = np.array(log_pitch)
    known = log_pitch[~np.isnan(log_pitch)]
    low, high = np.percentile(known, 15), np.percentile(known, 85)
    for _ in range(20):  # 1-D two-means clustering of the two voices
        middle = (low + high) / 2
        below, above = known[known <= middle], known[known > middle]
        if len(below) == 0 or len(above) == 0:
            break
        low, high = below.mean(), above.mean()
    middle = (low + high) / 2
    return np.where(np.isnan(log_pitch), 0, np.where(log_pitch > middle, 1, -1))


def choose_boundaries(
    gaps: list[tuple[int, int]], expected: list[float], speakers: list[Speaker], sides: np.ndarray
) -> list[int]:
    """Pick one gap per line boundary (increasing indices) minimising the total cost.

    The cost favours long pauses close to the expected position and, in duo mode, a change of voice.
    """
    n_lines, n_gaps = len(speakers), len(gaps)
    infinity = 1e18
    cost = np.full((n_lines, n_gaps + 1), infinity)  # cost[b, g + 1]: boundary b placed at gap g
    back = np.zeros((n_lines, n_gaps + 1), int)
    cost[0, :] = 0
    gap_length = np.array([b - a for a, b in gaps], float)
    for b in range(1, n_lines):
        best, best_gap = infinity, -1
        for g in range(n_gaps):
            if cost[b - 1, g] < best:  # previous boundary at a gap index < g
                best, best_gap = cost[b - 1, g], g
            if best_gap < 0:
                continue
            gap_middle = (gaps[g][0] + gaps[g][1]) / 2
            c = ((gap_middle - expected[b - 1]) / 300.0) ** 2 - 1.5 * np.log(gap_length[g] + 1)
            # speaker evidence: the segment before the gap should match line b, the one after line b + 1
            wanted = 1 if speakers[b - 1] == HIGHER_PITCH_SPEAKER else -1
            c -= 4.0 * sides[g] * wanted + 4.0 * sides[g + 1] * (-wanted)
            cost[b, g + 1] = best + c
            back[b, g + 1] = best_gap
    picks = []
    b, g = n_lines - 1, int(np.argmin(cost[n_lines - 1, :]))
    while b > 0:
        picks.append(g - 1)
        g = back[b, g]
        b -= 1
    return picks[::-1]


def align(project: Project, audio_path: Path) -> Alignment:
    """Measure the timing of every line of the project's text in the recording."""
    estimate = Timeline(project)
    samples = load_audio(audio_path)
    db = loudness_db(samples)
    n_frames = len(db)
    floor, peak = np.percentile(db, 10), np.percentile(db, 95)
    threshold = floor + 0.3 * (peak - floor)
    segments = speech_segments(db > threshold)
    n_lines = len(estimate.lines)
    if len(segments) < n_lines:
        raise CapsuleError(
            f"Seulement {len(segments)} passages de parole détectés pour {n_lines} paragraphes : "
            f"l’enregistrement correspond-il bien au texte ?"
        )
    speakers = [line.speaker for line in estimate.lines]
    # in solo mode there is a single voice, hence no speaker evidence
    sides = np.zeros(len(segments)) if project.solo else pitch_sides(samples, segments, n_frames)

    # candidate boundaries are the pauses; expected positions are proportional to the text length
    gaps = [(segments[k][1], segments[k + 1][0]) for k in range(len(segments) - 1)]
    speech_start, speech_end = segments[0][0], segments[-1][1]
    est_start, est_end = estimate.lines[0].start, estimate.lines[-1].end
    expected = [
        speech_start
        + ((estimate.lines[k].end + estimate.lines[k + 1].start) / 2 - est_start)
        / (est_end - est_start)
        * (speech_end - speech_start)
        for k in range(n_lines - 1)
    ]
    picks = choose_boundaries(gaps, expected, speakers, sides)
    bounds = [speech_start, *[edge for p in picks for edge in gaps[p]], speech_end]
    turns = [
        (bounds[2 * k] / FRAMES_PER_SECOND, bounds[2 * k + 1] / FRAMES_PER_SECOND) for k in range(n_lines)
    ]
    offset = INTRO - turns[0][0]

    # mouth envelopes: normalised loudness, smoothed, given to whoever speaks
    level = np.clip((db - threshold) / (peak - threshold), 0, 1)
    level = np.convolve(level, np.ones(4) / 4, "same")
    envelopes = {speaker: np.zeros(n_frames) for speaker in sorted(set(speakers))}
    for speaker, (a, b) in zip(speakers, turns, strict=True):
        i, j = int(a * FRAMES_PER_SECOND), int(b * FRAMES_PER_SECOND)
        envelopes[speaker][i:j] = level[i:j]

    lines = [(round(a + offset, 3), round(b + offset, 3)) for a, b in turns]
    duration = lines[-1][1] + END_HOLD + END_DURATION
    print(f"{len(segments)} passages de parole, décalage audio {offset:+.2f} s, durée {duration:.1f} s")
    for line, (a, b) in zip(estimate.lines, lines, strict=True):
        print(f"  {line.index:2d}  {a:7.2f} – {b:7.2f}  {line.text[:50]}")
    return Alignment(offset, lines, envelopes)
