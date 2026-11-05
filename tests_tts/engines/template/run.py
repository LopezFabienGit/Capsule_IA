#!/usr/bin/env python3
"""Moteur modèle : produit un bip par morceau, sans aucun modèle TTS.

Copier ce dossier pour ajouter un moteur. Il sert aussi à vérifier la chaîne
découpage -> assemblage -> rapport sans rien télécharger.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common import add_common_args, run_engine  # noqa: E402

SAMPLE_RATE = 24000
CHARS_PER_SECOND = 15


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = parser.parse_args()

    # À remplacer : charger le modèle ici.

    def synthesize(text: str, index: int) -> np.ndarray:
        # À remplacer : appeler le modèle et renvoyer un tableau audio mono.
        duration = len(text) / CHARS_PER_SECOND
        time_axis = np.arange(round(duration * SAMPLE_RATE)) / SAMPLE_RATE
        return 0.1 * np.sin(2 * np.pi * 440 * time_axis)

    # Tout réglage qui change le son va dans config : un essai ne peut pas en mélanger plusieurs.
    config = {"chars_per_second": CHARS_PER_SECOND, "pause_chunk": args.pause_chunk, "pause_section": args.pause_section}
    run_engine(args, "template", config, synthesize, SAMPLE_RATE)


if __name__ == "__main__":
    main()
