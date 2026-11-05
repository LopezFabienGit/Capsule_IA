"""Text of the video and when each paragraph is spoken."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import Project
from .errors import CapsuleError
from .speakers import DIALOGUE_LABELS, Speaker

INTRO = 3.2  # title card before the first line (s)
SPEAKING_RATE = 16.5  # estimated characters per second when there is no recording
GAP = 0.38  # estimated pause between lines (s)
END_HOLD = 0.9  # after the last line, before the end card (s)
END_DURATION = 4.2  # end card (s)


@dataclass
class Line:
    """One paragraph (or dialogue turn) and its time span in the video."""

    index: int  # 1-based
    speaker: Speaker
    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def read_text(project: Project) -> list[tuple[Speaker, str]]:
    """Non-empty lines of the text with their speaker.

    Duo mode: every line starts with « Person_1 : » or « Person_2 : ».
    Solo mode: every line goes to the presenter and the label is optional.
    """
    lines = []
    raw_lines = project.dialogue.read_text(encoding="utf8").strip().split("\n")
    for number, raw in enumerate(raw_lines, 1):
        if not raw.strip():
            continue
        label, separator, content = raw.partition(" : ")
        if not separator or label.strip() not in DIALOGUE_LABELS:
            if not project.solo:
                raise CapsuleError(
                    f"{project.dialogue.name} ligne {number} : en mode duo, elle doit commencer "
                    f"par « Person_1 : » ou « Person_2 : »"
                )
            content = raw
        speaker = project.presenter if project.solo else DIALOGUE_LABELS[label.strip()]
        lines.append((speaker, content.strip()))
    if not lines:
        raise CapsuleError(f"{project.dialogue.name} est vide")
    return lines


class Timeline:
    """Start and end of every line, either measured on the recording or estimated from text length."""

    def __init__(self, project: Project, timing_path: Path | None = None):
        text = read_text(project)
        self.lines: list[Line] = []
        if timing_path and timing_path.is_file():
            timing = json.loads(timing_path.read_text())
            if len(timing["lines"]) != len(text):
                raise CapsuleError(
                    f"{timing_path} contient {len(timing['lines'])} paragraphes mais le texte en a "
                    f"{len(text)} : relancer avec --realigner"
                )
            for i, ((speaker, content), (start, end)) in enumerate(
                zip(text, timing["lines"], strict=True), 1
            ):
                self.lines.append(Line(i, speaker, content, start, end))
            self.audio_offset = timing.get("audio_offset", INTRO)
        else:
            t = INTRO
            for i, (speaker, content) in enumerate(text, 1):
                duration = max(0.9, len(content) / SPEAKING_RATE + 0.25)
                self.lines.append(Line(i, speaker, content, t, t + duration))
                t += duration + GAP
            self.audio_offset = INTRO
        self.end_start = self.lines[-1].end + END_HOLD  # start of the end card
        self.duration = self.end_start + END_DURATION

    def line(self, i: int) -> Line:
        """Line i (1-based)."""
        return self.lines[i - 1]

    def start(self, i: int) -> float:
        return self.line(i).start

    def end(self, i: int) -> float:
        return self.line(i).end

    def at(self, i: int, fraction: float) -> float:
        """Time at a fraction (0..1) of line i."""
        line = self.line(i)
        return line.start + fraction * line.duration

    def cue(self, i: int, words: str) -> float:
        """Estimated time at which words are spoken in line i (proportional to their position in the text)."""
        content = self.line(i).text
        k = content.find(words)
        if k < 0:
            raise CapsuleError(f"« {words} » ne figure pas dans le paragraphe {i}")
        return self.at(i, k / len(content))
