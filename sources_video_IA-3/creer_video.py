#!/usr/bin/env python3
"""Fabrique une vidéo à partir d'un fichier de projet (.ini).

    python3 creer_video.py mon_projet.ini                 vidéo complète -> output/<nom>.mp4
    python3 creer_video.py mon_projet.ini --apercu 30,75  images fixes   -> output/apercus/
    python3 creer_video.py mon_projet.ini --de 60 --a 90  extrait        -> output/<nom>_60-90.mp4
    python3 creer_video.py mon_projet.ini --realigner     force un nouvel alignement de l'audio

L'alignement texte / voix est recalculé automatiquement quand l'audio, le texte ou le projet changent.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from capsule.alignment import align
from capsule.config import Project, load_project
from capsule.errors import CapsuleError
from capsule.renderer import Renderer
from capsule.timeline import read_text


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fabrique une vidéo à partir d’un fichier de projet.")
    parser.add_argument("projet", help="fichier de projet .ini")
    parser.add_argument("--apercu", help="instants (s) séparés par des virgules : produit des images fixes")
    parser.add_argument("--de", type=float, default=0.0, help="début de l’extrait (s)")
    parser.add_argument("--a", type=float, help="fin de l’extrait (s)")
    parser.add_argument(
        "--realigner", action="store_true", help="recalcule l’alignement même s’il est à jour"
    )
    return parser.parse_args(argv)


def alignment_is_current(project: Project) -> bool:
    """True when the saved alignment is newer than its inputs and covers every speaker of the text."""
    timing, envelopes = project.timing_path, project.envelope_path
    if not (timing.is_file() and envelopes.is_file()):
        return False
    inputs = (project.audio, project.dialogue, project.path)
    newest_input = max(p.stat().st_mtime for p in inputs)
    if min(timing.stat().st_mtime, envelopes.stat().st_mtime) < newest_input:
        return False
    speakers = {speaker.value for speaker, _ in read_text(project)}
    return speakers <= json.loads(envelopes.read_text()).keys()


def parse_times(text: str) -> list[float]:
    try:
        return [float(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise CapsuleError(
            f"--apercu attend des secondes séparées par des virgules (lu : {text!r})"
        ) from None


def extract_name(project: Project, start: float, end: float | None) -> Path:
    end_label = "fin" if end is None else f"{end:g}"
    return project.output_dir / f"{project.name}_{start:g}-{end_label}.mp4"


def run(args: argparse.Namespace) -> None:
    project = load_project(args.projet)
    if shutil.which("ffmpeg") is None:
        raise CapsuleError("ffmpeg est introuvable : l’installer (voir LISEZMOI.txt)")
    project.output_dir.mkdir(parents=True, exist_ok=True)

    timing = envelopes = None
    if project.audio:
        timing, envelopes = project.timing_path, project.envelope_path
        if args.realigner or not alignment_is_current(project):
            print(f"Alignement de {project.audio.name} sur {project.dialogue.name}…")
            align(project, project.audio).save(timing, envelopes)
    else:
        print("Pas d’audio : vidéo muette au minutage estimé.")

    with Renderer(project, timing, envelopes) as renderer:
        print(f"durée {renderer.timeline.duration:.2f} s", file=sys.stderr)
        if args.apercu:
            for path in renderer.write_stills(parse_times(args.apercu), project.output_dir / "apercus"):
                print(path)
            return
        is_extract = args.de or args.a is not None
        out = extract_name(project, args.de, args.a) if is_extract else project.video_path
        renderer.encode(out, project.audio, args.de, args.a)
        print(out)
        if project.write_srt:
            renderer.write_srt(project.srt_path)
            print(project.srt_path)


def main() -> None:
    try:
        run(parse_arguments())
    except CapsuleError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
