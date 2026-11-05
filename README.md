# Capsule IA

Outils pour produire des capsules pédagogiques vidéo à partir d'un script de narration.

| Dossier | Rôle | Documentation |
|---|---|---|
| `tests_tts/` | Génère et compare des narrations avec des modèles text-to-speech (VoxCPM2) | [README](tests_tts/README.md) |
| `sources_video_IA-3/` | Produit la vidéo animée à partir d'un texte et d'un enregistrement de voix | [LISEZMOI](sources_video_IA-3/LISEZMOI.txt) |

## Fichiers non versionnés

Ce dépôt ne contient que le code. Ces fichiers restent en local et sont à fournir pour produire une capsule :

- les voix de référence et leurs transcriptions ;
- les textes de narration : `text.txt` pour `tests_tts/`, `dialogue.txt` pour `sources_video_IA-3/` ;
- les audios et les vidéos, enregistrés ou générés.

Dans `sources_video_IA-3/`, le projet `chevre_ia.ini` a donc besoin de `dialogue.txt` et de `conversation.mp3` pour fonctionner. Les tests unitaires n'en dépendent pas :

```bash
cd sources_video_IA-3
python3 -m unittest discover tests
```
