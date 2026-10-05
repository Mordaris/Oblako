# Запуск проекта локально на Mac

1. Инструменты (Homebrew):
   ```bash
   brew install git ffmpeg python@3.11 node
   ```
2. Репозиторий:
   ```bash
   git clone https://github.com/Mordaris/Oblako.git
   cd Oblako
   git checkout claude/video-editing-ai-knowledge-base-vwkald
   ```
3. Python-зависимости для скриптов анализа:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install sherpa-onnx librosa soundfile opencv-python-headless scipy numpy pyyaml matplotlib fonttools
   ```
   Модели распознавания речи (GigaAM + Silero VAD) скрипт `scripts/transcribe.py` скачает сам в `~/.cache/oblako-models` (путь меняется переменной `MODELS_DIR`).
4. Проверка: `scripts/run_all.sh` (анализ ref01, ~3 мин). Для других референсов: `REF=ref02 python3 scripts/cuts.py` и т. д.
5. HyperFrames (для монтажа по команде): Node 22+, затем `npx hyperframes init <проект>`.
