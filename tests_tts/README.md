# Tests de modèles text-to-speech

Première étape de la pipeline texte → capsule vidéo : comparer des modèles TTS sur un même script, avec le même découpage et les mêmes mesures.

```
prepare_text.py     découpe le script en morceaux -> data/segments.json
common.py           reprise, assemblage et rapport, communs à tous les moteurs
engines/voxcpm/     VoxCPM2, avec son propre environnement Python
engines/template/   moteur factice à copier pour ajouter un modèle
exemples/script.txt exemple de script au format attendu
voices/             audios de référence pour le clonage (non versionnés)
data/               découpages générés (non versionnés)
runs/<moteur>/<essai>/   résultats (non versionnés)
    capsule.wav     narration complète
    chunks/         un fichier WAV par morceau
    config.json     réglages de l'essai
    report.json     durées par section, temps de calcul, mémoire
```

Chaque moteur a son propre environnement, car les modèles TTS ont souvent des dépendances incompatibles. Les voix, les scripts de narration et les audios générés ne sont pas versionnés.

## Prérequis

- Linux, [uv](https://docs.astral.sh/uv/) et ffmpeg ;
- pour VoxCPM2, un GPU NVIDIA avec au moins 10 Go de VRAM est conseillé ; le modèle pèse 5 Go à télécharger.

## Utilisation

Toutes les commandes se lancent depuis `tests_tts/`.

```bash
# 1. Installer l'environnement
uv sync --locked --project engines/voxcpm

# 2. Découper le script (à relancer s'il change)
uv run --locked --project engines/voxcpm python prepare_text.py --input chemin/vers/script.txt

# 3. Préparer une voix : ici, un extrait propre de 0:10 à 0:30
ffmpeg -ss 10 -t 20 -i source.mp3 -ac 1 voices/ma_voix.wav

# 4. Essai court : section 1 seulement
uv run --locked --project engines/voxcpm python engines/voxcpm/run.py \
    --device cuda --name essai1 --sections 1 \
    --reference voices/ma_voix.wav --prompt-text "$(tr -s ' \n' ' ' < voices/ma_voix.txt)"

# 5. Capsule complète, avec un nouveau nom d'essai
uv run --locked --project engines/voxcpm python engines/voxcpm/run.py \
    --device cuda --name complet \
    --reference voices/ma_voix.wav --prompt-text "$(tr -s ' \n' ' ' < voices/ma_voix.txt)"
```

`voices/ma_voix.txt` contient la transcription exacte de l'extrait. Sans transcription, retirez `--prompt-text`. Sans voix de référence, utilisez `--voice-description "(Une voix féminine posée et claire)"`.

Si un essai s'arrête, relancez-le avec le même `--name` : les morceaux déjà générés sont conservés. Avec d'autres réglages ou un autre découpage, le script demande de changer de nom pour ne pas mélanger les résultats. Pour comparer des réglages (`--cfg`, `--steps`, `--seed`), donnez donc un nom à chaque essai.

## VoxCPM2 : à savoir

- **GPU anciens :** `torch.compile` exige une carte de CUDA capability 7.0 ou plus. En dessous (par exemple une Quadro P6000), ajoutez `--no-optimize`.
- **Version de CUDA :** le verrou installe PyTorch 2.7.1 pour CUDA 11.8, afin de fonctionner avec un pilote limité à CUDA 12.1.
- **Mesures :** sur une Quadro P6000 avec `--no-optimize`, une narration de 5 min 31 a pris environ 2,4 fois sa durée, avec un pic de 9,7 Go de VRAM (référence de 73 s avec sa transcription). Le premier morceau est nettement plus lent que les suivants.
- **Chiffres :** ils sont envoyés tels quels au modèle. `normalize=True` n'est pas utilisé, car hors chinois VoxCPM applique un normaliseur anglais. Il faut donc écrire les nombres en toutes lettres dans le texte ; `prepare_text.py` signale ceux qui restent.
- **Texte long :** la documentation recommande de découper, car un texte long peut accélérer la voix, faire bourdonner le son ou saturer la mémoire. D'où les morceaux de 300 caractères au maximum (`--max-chars`).
- **Bourdonnement :** la documentation conseille d'essayer `--cfg 1.5`.

## Ajouter un modèle

1. Copier `engines/template/` vers `engines/<modèle>/`.
2. Dans `pyproject.toml`, changer le nom et ajouter les dépendances du modèle.
3. Dans `run.py`, charger le modèle, remplir `synthesize()`, puis remplacer `"template"` par le nom du moteur.

Le moteur factice vérifie la chaîne sans modèle :

```bash
uv run --project engines/template python prepare_text.py --input exemples/script.txt
uv run --project engines/template python engines/template/run.py --sections 1,2
```
