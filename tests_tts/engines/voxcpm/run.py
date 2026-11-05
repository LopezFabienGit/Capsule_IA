#!/usr/bin/env python3
"""Génère la narration avec VoxCPM2.

Trois façons de choisir la voix :
  --reference                       clonage depuis un extrait audio
  --reference + --prompt-text       clonage plus fidèle, avec la transcription exacte de l'extrait
  --voice-description               voix décrite en texte ; avec --reference, consigne de style
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from voxcpm import VoxCPM

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common import add_common_args, run_engine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_common_args(parser)
    parser.add_argument("--model", default="openbmb/VoxCPM2", help="dépôt Hugging Face ou dossier local")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda ou cuda:N (défaut : auto)")
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="désactive torch.compile, indispensable sur les GPU trop anciens pour Triton (CUDA capability < 7.0)",
    )
    parser.add_argument("--reference", type=Path, help="audio de référence pour le clonage")
    parser.add_argument("--prompt-text", help="transcription exacte de --reference")
    parser.add_argument("--voice-description", help='ex. "(Une voix féminine posée et claire)"')
    parser.add_argument("--denoise", action="store_true", help="débruite l'audio de référence")
    parser.add_argument("--cfg", type=float, default=2.0, help="guidage (essayer 1.5 si le son bourdonne)")
    parser.add_argument("--steps", type=int, default=10, help="nombre d'étapes de diffusion")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Vérifié avant le chargement du modèle, qui prend du temps.
    if args.prompt_text and not args.reference:
        parser.error("--prompt-text nécessite --reference")
    if args.prompt_text and args.voice_description:
        parser.error("--voice-description ne se combine pas avec --prompt-text")
    if args.reference and not args.reference.is_file():
        parser.error(f"--reference : fichier introuvable : {args.reference}")

    started = time.perf_counter()
    model = VoxCPM.from_pretrained(
        args.model, load_denoiser=args.denoise, device=args.device, optimize=not args.no_optimize
    )
    load_seconds = time.perf_counter() - started

    reference = str(args.reference) if args.reference else None
    prefix = args.voice_description or ""

    def synthesize(text: str, index: int) -> np.ndarray:
        torch.manual_seed(args.seed + index)
        return model.generate(
            text=prefix + text,
            reference_wav_path=reference,
            # La documentation conseille le même extrait aux deux endroits pour la meilleure fidélité.
            prompt_wav_path=reference if args.prompt_text else None,
            prompt_text=args.prompt_text,
            cfg_value=args.cfg,
            inference_timesteps=args.steps,
            denoise=args.denoise,
        )

    # --device et --no-optimize ne sont pas dans config : un essai commencé sur CPU peut se terminer sur GPU.
    config = {
        "model": args.model,
        "reference": reference,
        "prompt_text": args.prompt_text,
        "voice_description": args.voice_description,
        "denoise": args.denoise,
        "cfg": args.cfg,
        "steps": args.steps,
        "seed": args.seed,
        "pause_chunk": args.pause_chunk,
        "pause_section": args.pause_section,
    }
    run_engine(args, "voxcpm", config, synthesize, model.tts_model.sample_rate, load_seconds)


if __name__ == "__main__":
    main()
