"""Склейки и движение по кадрам.

1. ffmpeg scene score для каждого кадра (lavfi.scene_score) -> analysis/scene_scores.csv
2. Склейки: scene_score >= CUT_T и локальный максимум -> analysis/cuts.csv
   (порог подобран по контакт-листам, см. docs/implementation-plan.md, Фаза 1)
3. Движение: средняя абсолютная разница яркости соседних кадров (64x36 luma) -> analysis/motion.csv
4. Сводка по планам: ASL, медиана -> analysis/shots.csv + печать
5. Крупные изменения кадра за ±5 кадров (RGB 64x36, порог 28), не совпадающие со склейкой:
   влёты графики, плавные переходы -> analysis/events.csv

Запуск: python3 scripts/cuts.py
"""
import csv
import re
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reference" / "ref01.mp4"
OUT = ROOT / "analysis"
FPS = 2997 / 100
CUT_T = 0.10      # порог scene score для склейки
MIN_GAP = 6       # кадров между склейками (не считать двойные срабатывания на переходах)


def scene_scores():
    txt = OUT / "scene_scores.txt"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC), "-an", "-vf",
         f"select='gte(scene,0)',metadata=print:file={txt}", "-f", "null", "-"], check=True)
    rows, cur = [], None
    for line in txt.read_text().splitlines():
        m = re.match(r"frame:(\d+)\s+pts:\d+\s+pts_time:([\d.]+)", line)
        if m:
            cur = (int(m.group(1)), float(m.group(2)))
        m = re.match(r"lavfi.scene_score=([\d.]+)", line)
        if m:
            rows.append((cur[0], cur[1], float(m.group(1))))
    txt.unlink()
    return rows


def rgb_small():
    w, h = 64, 36
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC), "-an", "-vf", f"scale={w}:{h}", "-pix_fmt", "rgb24",
         "-f", "rawvideo", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32)


def luma_motion():
    w, h = 64, 36
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC), "-an", "-vf", f"scale={w}:{h},format=gray",
         "-f", "rawvideo", "-"], check=True, capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    diff = np.r_[0, np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))]
    return fr, diff


def main():
    OUT.mkdir(exist_ok=True)
    sc = scene_scores()
    _, mot = luma_motion()
    s = np.array([r[2] for r in sc])
    with open(OUT / "scene_scores.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t", "scene", "motion"])
        for (n, t, v), m in zip(sc, mot):
            wr.writerow([n, f"{t:.3f}", f"{v:.4f}", f"{m:.2f}"])

    cuts = []
    for i in range(1, len(s) - 1):
        if s[i] >= CUT_T and s[i] >= s[i - 1] and s[i] >= s[i + 1]:
            if cuts and i - cuts[-1] < MIN_GAP:
                if s[i] > s[cuts[-1]]:
                    cuts[-1] = i
                continue
            cuts.append(i)
    with open(OUT / "cuts.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["cut", "frame", "t", "scene"])
        for k, i in enumerate(cuts, 1):
            wr.writerow([k, i, f"{i / FPS:.3f}", f"{s[i]:.3f}"])

    bounds = [0] + cuts + [len(s)]
    lens = np.diff(bounds) / FPS
    with open(OUT / "shots.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["shot", "start", "end", "dur_s", "frames"])
        for k in range(len(lens)):
            wr.writerow([k + 1, f"{bounds[k] / FPS:.3f}", f"{bounds[k + 1] / FPS:.3f}", f"{lens[k]:.3f}",
                         bounds[k + 1] - bounds[k]])

    with open(OUT / "motion.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t", "motion"])
        for i, m in enumerate(mot):
            wr.writerow([i, f"{i / FPS:.3f}", f"{m:.2f}"])

    fr, K = rgb_small(), 5
    d = np.zeros(len(fr))
    d[K:-K] = np.abs(fr[2 * K:] - fr[:-2 * K]).mean(axis=(1, 2, 3))
    with open(OUT / "events.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t", "diff10", "near_cut_frames"])
        for i in range(K, len(d) - K):
            if d[i] >= 28 and d[i] == d[max(0, i - 8):i + 9].max():
                near = min(abs(i - c) for c in cuts) if cuts else 999
                wr.writerow([i, f"{i / FPS:.3f}", f"{d[i]:.1f}", near])

    print(f"кадров {len(s)}, склеек {len(cuts)}, планов {len(lens)}")
    print(f"ASL {lens.mean():.2f} с, медиана {np.median(lens):.2f} с, мин {lens.min():.2f}, макс {lens.max():.2f}")


if __name__ == "__main__":
    main()
