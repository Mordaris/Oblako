"""Цифровой зум/сдвиг кадра говорящей головы относительно эталонного общего плана.

Камера в референсе статична, все планы спикера — кропы одного исходника. Поэтому масштаб
каждого кадра относительно кадра 0 (самый общий план) = цифровой зум монтажёра.
ORB + estimateAffinePartial2D (подобие: масштаб, поворот, сдвиг), RANSAC.
Кадры графики (мало инлаеров) -> пустые значения.

Выход: analysis/zoom.csv  (frame, t, scale, tx_px, ty_px, inliers), px — в координатах 1280x720
Запуск: python3 scripts/zoom_track.py
"""
import csv
import subprocess
from pathlib import Path

import cv2
import numpy as np

from refcfg import FPS, OUT, SRC

ROOT = Path(__file__).resolve().parent.parent
W, H = 640, 360
MIN_INL = 40
REF_T = float(__import__("os").environ.get("ZOOM_REF_T", "0"))   # время эталонного общего плана, с


def frames():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(SRC), "-an", "-vf", f"scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W)


def main():
    orb = cv2.ORB_create(3000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref_kp = ref_des = None
    rows = []
    for i, f in enumerate(frames()):
        kp, des = orb.detectAndCompute(f, None)
        if ref_des is None:
            if i < int(REF_T * FPS):
                rows.append([i, f"{i / FPS:.3f}", "", "", "", 0])
                continue
            ref_kp, ref_des = kp, des
            rows.append([i, f"{i / FPS:.3f}", "1.0000", "0.0", "0.0", len(kp)])
            continue
        row = [i, f"{i / FPS:.3f}", "", "", "", 0]
        if des is not None and len(kp) > 50:
            m = bf.match(ref_des, des)
            if len(m) > MIN_INL:
                src = np.float32([ref_kp[x.queryIdx].pt for x in m])
                dst = np.float32([kp[x.trainIdx].pt for x in m])
                M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0)
                k = int(inl.sum()) if inl is not None else 0
                if M is not None and k >= MIN_INL:
                    s = float(np.hypot(M[0, 0], M[1, 0]))
                    # сдвиг центра кадра, пересчёт в пиксели 1280x720
                    cx, cy = W / 2, H / 2
                    nx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx
                    ny = M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy
                    row = [i, f"{i / FPS:.3f}", f"{s:.4f}", f"{nx * 1280 / W:.1f}", f"{ny * 720 / H:.1f}", k]
        rows.append(row)
    with open(OUT / "zoom.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "t", "scale", "tx_px", "ty_px", "inliers"])
        w.writerows(rows)
    ok = [float(r[2]) for r in rows if r[2]]
    print(f"кадров {len(rows)}, с оценкой масштаба {len(ok)}, масштаб min {min(ok):.3f} max {max(ok):.3f}")


if __name__ == "__main__":
    main()
