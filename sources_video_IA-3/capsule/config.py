"""Project file (.ini): one file describes one video.

The [video] section holds the text, the audio and the options; each [media ...] section declares an
image or a video clip shown in the white panel. Relative paths are resolved from the project file.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import CapsuleError
from .speakers import PRESENTER_NAMES, Speaker

PACKAGE_DIR = Path(__file__).resolve().parent
SCENES_DIR = PACKAGE_DIR / "scenes"
DEFAULT_OUTPUT_DIR = PACKAGE_DIR.parent / "output"
MEDIA_ZONES = ("panneau", "haut", "bas", "gauche", "droite")
NO_ILLUSTRATIONS = ("", "aucune", "non")
YES, NO = ("oui", "yes", "true", "1", "on"), ("non", "no", "false", "0", "off")


@dataclass(frozen=True)
class MediaSpec:
    """An image or video clip to show in the panel, as declared in a [media ...] section."""

    section: str
    file: Path
    caption: str = ""
    zone: str = "panneau"
    hide_illustration: bool = True
    loop: bool = False
    paragraph: int | None = None  # 1-based index of a non-empty line of the text
    from_words: str = ""  # optional words of that paragraph from which the media appears
    start: float | None = None  # absolute start time (s), used when no paragraph is given
    duration: float | None = None  # default: until the end of the paragraph (or 5 s)


@dataclass(frozen=True)
class Project:
    path: Path
    name: str
    dialogue: Path
    audio: Path | None
    solo: bool
    presenter: Speaker
    presenter_on_left: bool
    illustrations: str | None  # module name in capsule/scenes, or None for a blank panel
    title: str
    subtitles: bool
    write_srt: bool
    normalize_audio: bool
    output_dir: Path
    media: list[MediaSpec] = field(default_factory=list)

    @property
    def video_path(self) -> Path:
        return self.output_dir / f"{self.name}.mp4"

    @property
    def srt_path(self) -> Path:
        return self.output_dir / f"{self.name}.srt"

    @property
    def alignment_dir(self) -> Path:
        return self.output_dir / "alignement"

    @property
    def timing_path(self) -> Path:
        return self.alignment_dir / f"{self.name}_timing.json"

    @property
    def envelope_path(self) -> Path:
        return self.alignment_dir / f"{self.name}_env.json"


class _Section:
    """Typed accessors on one section of the project file, with French error messages."""

    def __init__(self, section: configparser.SectionProxy, base_dir: Path):
        self.section, self.base_dir = section, base_dir

    def error(self, message: str) -> CapsuleError:
        return CapsuleError(f"Erreur de configuration : [{self.section.name}] {message}")

    def text(self, key: str, default: str = "") -> str:
        return self.section.get(key, default).strip()

    def path(self, key: str, default: str = "", must_exist: bool = True) -> Path | None:
        value = self.text(key, default)
        if not value:
            return None
        path = (self.base_dir / os.path.expanduser(value)).resolve()
        if must_exist and not path.is_file():
            raise self.error(f"{key} : fichier introuvable : {path}")
        return path

    def yes_no(self, key: str, default: str) -> bool:
        value = self.text(key, default).lower()
        if value in YES:
            return True
        if value in NO:
            return False
        raise self.error(f"{key} doit valoir « oui » ou « non » (lu : {value!r})")

    def choice(self, key: str, default: str, allowed: tuple[str, ...]) -> str:
        value = self.text(key, default)
        for option in allowed:
            if option.lower() == value.lower():
                return option
        raise self.error(f"{key} doit valoir {' | '.join(allowed)} (lu : {value!r})")

    def seconds(self, key: str) -> float | None:
        value = self.text(key)
        if not value:
            return None
        try:
            return float(value.replace(",", "."))
        except ValueError:
            raise self.error(f"{key} doit être un nombre de secondes (lu : {value!r})") from None

    def positive_int(self, key: str) -> int | None:
        value = self.text(key)
        if not value:
            return None
        if not value.isdigit() or int(value) < 1:
            raise self.error(f"{key} doit être un numéro (lu : {value!r})")
        return int(value)


def _read_media(section: _Section) -> MediaSpec:
    if not section.text("fichier"):
        raise section.error("indiquer le fichier (fichier = ...)")
    spec = MediaSpec(
        section=section.section.name,
        file=section.path("fichier"),
        caption=section.text("legende"),
        zone=section.choice("zone", "panneau", MEDIA_ZONES),
        hide_illustration=section.yes_no("masquer_illustration", "oui"),
        loop=section.yes_no("boucle", "non"),
        paragraph=section.positive_int("paragraphe"),
        from_words=section.text("a_partir_de"),
        start=section.seconds("debut"),
        duration=section.seconds("duree"),
    )
    if spec.paragraph is None and spec.start is None:
        raise section.error("indiquer « paragraphe = N » ou « debut = secondes »")
    return spec


def load_project(path: str | Path) -> Project:
    """Read and validate a project file; raises CapsuleError with a message for the user."""
    path = Path(path).resolve()
    if not path.is_file():
        raise CapsuleError(f"Fichier de projet introuvable : {path}")
    parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"), interpolation=None)
    parser.read(path, encoding="utf8")
    if not parser.has_section("video"):
        raise CapsuleError(f"{path} doit contenir une section [video]")
    base_dir = path.parent
    video = _Section(parser["video"], base_dir)

    illustrations = video.text("illustrations", "aucune")
    if illustrations.lower() in NO_ILLUSTRATIONS:
        illustrations = None
    elif not (SCENES_DIR / f"{illustrations}.py").is_file():
        available = sorted(p.stem for p in SCENES_DIR.glob("*.py") if not p.stem.startswith("_"))
        raise video.error(
            f"illustrations : « {illustrations} » inconnu (disponibles : {', '.join(available)})"
        )

    dialogue = video.path("dialogue", "dialogue.txt")
    if dialogue is None:
        raise video.error("dialogue : indiquer le fichier texte")
    output = video.text("dossier_sortie")
    return Project(
        path=path,
        name=video.text("nom") or path.stem,
        dialogue=dialogue,
        audio=video.path("audio"),
        solo=video.choice("mode", "duo", ("duo", "solo")) == "solo",
        presenter=PRESENTER_NAMES[video.choice("presentateur", "Person_2", tuple(PRESENTER_NAMES))],
        presenter_on_left=video.choice("position", "gauche", ("gauche", "droite")) == "gauche",
        illustrations=illustrations,
        title=video.text("titre"),
        subtitles=video.yes_no("sous_titres", "oui"),
        write_srt=video.yes_no("fichier_srt", "non"),
        normalize_audio=video.yes_no("normaliser_audio", "oui"),
        output_dir=(base_dir / output).resolve() if output else DEFAULT_OUTPUT_DIR,
        media=[
            _read_media(_Section(parser[name], base_dir))
            for name in parser.sections()
            if name.lower().startswith("media")
        ],
    )
