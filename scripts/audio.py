"""Звук: онсеты, энергия по полосам, кандидаты в SFX и музыка.

Выход:
  analysis/onsets.csv  — онсеты: t, сила, RMS dB, центроид Гц, энергия полос low/mid/high dB,
                         расстояние до ближайшего начала слова, флаг sfx_candidate
  analysis/bands.csv   — огибающие полос (шаг 100 мс) для поиска райзеров, музыкальной подложки
  печать: темп музыки (если найден), доля склеек, совпадающих с онсетом (±2 кадра)

Кандидат в SFX: онсет не ближе 60 мс к началу слова И (high-полоса > mid-полоса − 6 dB
ИЛИ low-полоса растёт > 6 dB за 50 мс). Тип звука — гипотеза, слушать нечем.
Запуск: python3 scripts/audio.py
"""
import csv
import json
import subprocess
from pathlib import Path

import librosa
import numpy as np

from refcfg import FPS, OUT, SRC

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
HOP = 441  # 10 мс


def load():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(SRC), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-6))


def main():
    y = load()
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=2048)
    band = lambda lo, hi: np.sqrt((S[(f >= lo) & (f < hi)] ** 2).mean(axis=0))
    low, mid, high = band(20, 150), band(150, 4000), band(4000, 16000)
    rms = librosa.feature.rms(S=S, frame_length=2048)[0]
    cent = librosa.feature.spectral_centroid(S=S, sr=SR)[0]
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S), sr=SR, hop_length=HOP)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, backtrack=False, delta=0.15)
    times = librosa.frames_to_time(on, sr=SR, hop_length=HOP)

    tr = json.loads((OUT / "transcript.json").read_text(encoding="utf-8"))
    wstarts = np.array([w["start"] for p in tr["phrases"] for w in p["words"]])
    cuts = np.array([float(r["t"]) for r in csv.DictReader(open(OUT / "cuts.csv"))])

    rows = []
    for fr, t in zip(on, times):
        dw = float(np.min(np.abs(wstarts - t))) if len(wstarts) else 99
        lo_jump = db(low[fr]) - db(low[max(fr - 5, 0)])
        hi_rel = db(high[fr]) - db(mid[fr])
        sfx = dw > 0.06 and (hi_rel > -6 or lo_jump > 6)
        dc = float(np.min(np.abs(cuts - t))) if len(cuts) else 99
        rows.append([f"{t:.3f}", f"{env[fr]:.2f}", f"{db(rms[fr]):.1f}", f"{cent[fr]:.0f}", f"{db(low[fr]):.1f}",
                     f"{db(mid[fr]):.1f}", f"{db(high[fr]):.1f}", f"{dw:.3f}", f"{dc:.3f}", int(sfx)])
    with open(OUT / "onsets.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "strength", "rms_db", "centroid_hz", "low_db", "mid_db", "high_db",
                    "dist_word_s", "dist_cut_s", "sfx_candidate"])
        w.writerows(rows)

    step = 10  # 100 мс
    with open(OUT / "bands.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "rms_db", "low_db", "mid_db", "high_db", "centroid_hz"])
        for i in range(0, S.shape[1], step):
            sl = slice(i, i + step)
            w.writerow([f"{i * HOP / SR:.2f}", f"{db(rms[sl].mean()):.1f}", f"{db(low[sl].mean()):.1f}",
                        f"{db(mid[sl].mean()):.1f}", f"{db(high[sl].mean()):.1f}", f"{cent[sl].mean():.0f}"])

    tempo, _ = librosa.beat.beat_track(y=y, sr=SR)
    tol = 2 / FPS
    hit = sum(1 for c in cuts if np.min(np.abs(times - c)) <= tol)
    print(f"онсетов {len(times)}, кандидатов SFX {sum(r[-1] for r in rows)}")
    print(f"оценка темпа {float(np.atleast_1d(tempo)[0]):.1f} BPM (на речи ненадёжна)")
    print(f"склеек с онсетом в ±2 кадра: {hit}/{len(cuts)}")


if __name__ == "__main__":
    main()
