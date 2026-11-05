"""Socle commun : même découpage, mêmes fichiers de sortie et mêmes mesures pour tous les moteurs.

Un moteur fournit une fonction synthesize(text, index) -> tableau audio mono et
sa fréquence d'échantillonnage. Le reste (reprise, assemblage, rapport) est ici.
"""
import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--segments", type=Path, default=ROOT / "data" / "segments.json")
    parser.add_argument("--name", help="nom de l'essai ; réutiliser un nom reprend cet essai (défaut : date)")
    parser.add_argument("--sections", help="sections à générer, ex. 1,2,16 (défaut : toutes)")
    parser.add_argument("--pause-chunk", type=float, default=0.25, help="silence entre morceaux (s)")
    parser.add_argument("--pause-section", type=float, default=0.7, help="silence entre sections (s)")


def _select_sections(segments: list[dict], selection: str | None) -> list[dict]:
    if not selection:
        return segments
    wanted = {int(value) for value in selection.split(",")}
    unknown = wanted - {section["section"] for section in segments}
    if unknown:
        raise SystemExit(f"Sections inconnues : {sorted(unknown)}")
    return [section for section in segments if section["section"] in wanted]


def _prepare_run_dir(args: argparse.Namespace, engine: str, config: dict) -> Path:
    if not args.segments.exists():
        raise SystemExit(f"{args.segments} introuvable : lancez d'abord prepare_text.py")
    name = args.name or time.strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / engine / name
    (run_dir / "chunks").mkdir(parents=True, exist_ok=True)

    # Interdit de mélanger dans un même essai des morceaux issus de réglages différents.
    full_config = {
        **config,
        "segments_sha256": hashlib.sha256(args.segments.read_bytes()).hexdigest(),
    }
    config_path = run_dir / "config.json"
    if config_path.exists() and json.loads(config_path.read_text(encoding="utf-8")) != full_config:
        raise SystemExit(f"L'essai « {name} » existe avec d'autres réglages : changez de --name.")
    config_path.write_text(json.dumps(full_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Essai : {run_dir} (relancer avec --name {name} pour reprendre)")
    return run_dir


def _peak_memory() -> dict:
    peak = {"peak_ram_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)}
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        peak["peak_vram_gb"] = round(torch.cuda.max_memory_reserved() / 1e9, 2)
    return peak


def run_engine(
    args: argparse.Namespace,
    engine: str,
    config: dict,
    synthesize: Callable[[str, int], np.ndarray],
    sample_rate: int,
    load_seconds: float = 0.0,
) -> Path:
    all_segments = json.loads(args.segments.read_text(encoding="utf-8"))
    sections = _select_sections(all_segments, args.sections)
    run_dir = _prepare_run_dir(args, engine, config)

    total = sum(len(section["chunks"]) for section in sections)
    done = 0
    generation_seconds = 0.0
    generated_audio_seconds = 0.0
    audio_parts: list[np.ndarray] = []
    report_sections = []
    position = 0.0

    for section_index, section in enumerate(sections):
        section_start = position
        for chunk_index, text in enumerate(section["chunks"], start=1):
            done += 1
            path = run_dir / "chunks" / f"s{section['section']:02d}_c{chunk_index:02d}.wav"
            if path.exists():
                wav, file_rate = sf.read(path, dtype="float32")
                if file_rate != sample_rate:
                    raise SystemExit(f"{path} : {file_rate} Hz au lieu de {sample_rate} Hz")
                print(f"[{done}/{total}] {path.name} déjà généré")
            else:
                started = time.perf_counter()
                # Graine stable par morceau : une reprise donne le même résultat qu'un essai d'une traite.
                wav = np.asarray(
                    synthesize(text, section["section"] * 1000 + chunk_index), dtype=np.float32
                ).squeeze()
                elapsed = time.perf_counter() - started
                generation_seconds += elapsed
                generated_audio_seconds += len(wav) / sample_rate
                # Écriture atomique : un arrêt brutal ne laisse pas de morceau tronqué à reprendre.
                temporary = path.with_suffix(".tmp")
                sf.write(temporary, wav, sample_rate, format="WAV")
                temporary.replace(path)
                print(f"[{done}/{total}] {path.name} : {len(wav) / sample_rate:.1f} s en {elapsed:.1f} s")

            audio_parts.append(wav)
            position += len(wav) / sample_rate
            is_last_chunk = chunk_index == len(section["chunks"])
            is_last_section = section_index == len(sections) - 1
            if not (is_last_chunk and is_last_section):
                pause = args.pause_section if is_last_chunk else args.pause_chunk
                audio_parts.append(np.zeros(round(pause * sample_rate), dtype=np.float32))
                position += pause

        report_sections.append(
            {
                "section": section["section"],
                "title": section["title"],
                "start_s": round(section_start, 2),
                "duration_s": round(position - section_start, 2),
                "target_start_s": section["target_start_s"],
                "target_duration_s": section["target_duration_s"],
            }
        )

    output = run_dir / "capsule.wav"
    sf.write(output, np.concatenate(audio_parts), sample_rate, format="WAV")

    report = {
        "engine": engine,
        "config": config,
        "sections_selected": [section["section"] for section in sections],
        "duration_s": round(position, 2),
        "sample_rate": sample_rate,
        "load_seconds": round(load_seconds, 1),
        "generation_seconds": round(generation_seconds, 1),
        "real_time_factor": round(generation_seconds / generated_audio_seconds, 3)
        if generated_audio_seconds
        else None,
        **_peak_memory(),
        "sections": report_sections,
    }
    (run_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{output}")
    print(f"Durée : {position // 60:.0f} min {position % 60:.0f} s")
    print(f"Temps de calcul / durée audio : {report['real_time_factor']}")
    print(f"Mémoire : {_peak_memory()}")
    return output
