"""Общие пути для анализа референса. Референс выбирается переменной окружения REF (по умолчанию ref01).

REF=ref01 -> reference/ref01.mp4, результаты в analysis/          (исторически)
REF=refNN -> reference/refNN.mp4, результаты в analysis/refNN/
FPS берётся из файла (ffprobe r_frame_rate).
"""
import os
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = os.environ.get("REF", "ref01")
SRC = ROOT / "reference" / f"{REF}.mp4"
OUT = ROOT / "analysis" if REF == "ref01" else ROOT / "analysis" / REF
OUT.mkdir(parents=True, exist_ok=True)
EVENTS = ROOT / "kb" / f"{REF}_events.csv"
FPS = float(Fraction(subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
     str(SRC)], check=True, capture_output=True, text=True).stdout.strip()))
