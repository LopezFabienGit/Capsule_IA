#!/usr/bin/env python3
"""Découpe un script de narration en morceaux prêts pour la synthèse vocale.

Entrée : sections « ### N. Titre — M:SS » suivies du texte à prononcer.
Sortie : data/segments.json, commun à tous les moteurs TTS.
Les titres et les tirets de liste ne sont pas prononcés. Le texte n'est pas
réécrit : les chiffres restants sont seulement signalés.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = re.compile(r"^#{2,}\s*(\d+)\.\s*(.+?)\s*[—–-]\s*(\d+):(\d{2})\s*$")


def parse_sections(script: str) -> list[dict]:
    sections: list[dict] = []
    for line in script.splitlines():
        line = line.strip()
        if not line or line.startswith("# "):
            continue
        if line.startswith("#"):
            match = HEADER.match(line)
            if not match:
                raise ValueError(f"Titre de section non reconnu : {line!r}")
            number, title, minutes, seconds = match.groups()
            sections.append(
                {
                    "section": int(number),
                    "title": title,
                    "target_start_s": int(minutes) * 60 + int(seconds),
                    "lines": [],
                }
            )
        elif sections:
            sections[-1]["lines"].append(re.sub(r"^[-*]\s+", "", line))
    return sections


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"([,;:])\1+", r"\1", text).strip()


def pack(parts: list[str], max_chars: int) -> list[str]:
    """Regroupe des morceaux consécutifs sans dépasser max_chars si possible."""
    chunks: list[str] = []
    for part in parts:
        if chunks and len(chunks[-1]) + 1 + len(part) <= max_chars:
            chunks[-1] += " " + part
        else:
            chunks.append(part)
    return chunks


def split_text(text: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        if len(sentence) <= max_chars:
            parts.append(sentence)
        else:
            parts.extend(pack(re.split(r"(?<=[,;:])\s+", sentence), max_chars))
    return pack(parts, max_chars)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT.parent / "text.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "segments.json")
    parser.add_argument("--max-chars", type=int, default=300)
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"{args.input} introuvable : indiquez le script avec --input")
    sections = parse_sections(args.input.read_text(encoding="utf-8"))
    if not sections:
        raise SystemExit(f"Aucune section trouvée dans {args.input}")
    for section, following in zip(sections, sections[1:] + [None]):
        section["target_duration_s"] = (
            following["target_start_s"] - section["target_start_s"] if following else None
        )
        section["chunks"] = split_text(clean(" ".join(section.pop("lines"))), args.max_chars)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chunks = [chunk for section in sections for chunk in section["chunks"]]
    print(
        f"{len(sections)} sections, {len(chunks)} morceaux, "
        f"{sum(map(len, chunks))} caractères, "
        f"{max(map(len, chunks))} caractères au maximum par morceau -> {args.output}"
    )
    for section in sections:
        for chunk in section["chunks"]:
            for token in re.findall(r"\S*\d\S*", chunk):
                print(f"  à vérifier, section {section['section']} : chiffres dans {token!r}")


if __name__ == "__main__":
    main()
