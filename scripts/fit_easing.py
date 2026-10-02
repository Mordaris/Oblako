"""Подбор cubic-bezier(x1,y1,x2,y2) по покадровым значениям анимируемого параметра.

Использование как модуль: fit(values) -> (x1, y1, x2, y2, rmse)
Запуск: python3 scripts/fit_easing.py  — фит всех зум-рампов из analysis/zoom.csv,
         результат: analysis/easing_zoom.csv
"""
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from refcfg import FPS, OUT

ROOT = Path(__file__).resolve().parent.parent


def bezier_y_at_x(x1, y1, x2, y2, xs):
    s = np.linspace(0, 1, 400)
    bx = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3
    by = 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3
    return np.interp(xs, bx, by)


def fit(values):
    v = np.asarray(values, float)
    p = (v - v[0]) / (v[-1] - v[0])
    xs = np.linspace(0, 1, len(p))
    loss = lambda q: np.mean((bezier_y_at_x(*q, xs) - p) ** 2)
    best = None
    for init in ([0.25, 0.1, 0.25, 1], [0.42, 0, 0.58, 1], [0, 0, 0.2, 1], [0.6, 0, 1, 1]):
        r = minimize(loss, init, bounds=[(0, 1), (-0.5, 1.5), (0, 1), (-0.5, 1.5)], method="L-BFGS-B")
        if best is None or r.fun < best.fun:
            best = r
    return (*np.round(best.x, 2), float(np.sqrt(best.fun)))


def main():
    z = list(csv.DictReader(open(OUT / "zoom.csv")))
    sc = np.array([float(r["scale"]) if r["scale"] else np.nan for r in z])
    # рампы: участки, где масштаб меняется > 0,15%/кадр не меньше 6 кадров подряд (вне склеек — склейка даёт скачок за 1 кадр)
    d = np.abs(np.diff(sc))
    mv = np.nan_to_num(d) > 0.0015
    ramps, i = [], 0
    while i < len(mv):
        if mv[i]:
            j = i
            while j < len(mv) and mv[j]:
                j += 1
            if j - i >= 6 and np.nanmax(d[i:j]) < 0.05 and abs(np.nansum(np.diff(sc)[i:j])) >= 0.03:
                ramps.append(((i - 2) / FPS, (j + 2) / FPS))
            i = j
        else:
            i += 1
    rows = []
    for a, b in ramps:
        seg = sc[int(a * FPS):int(b * FPS) + 1]
        seg = seg[~np.isnan(seg)]
        # обрезать плато: от первого кадра изменения до последнего
        d = np.abs(np.diff(seg))
        on = np.where(d > 0.0015)[0]
        if len(on) < 2:
            continue
        seg = seg[on[0]:on[-1] + 2]
        x1, y1, x2, y2, err = fit(seg)
        rows.append([a, b, len(seg) - 1, round((len(seg) - 1) / FPS * 1000), round(seg[0], 3), round(seg[-1], 3),
                     x1, y1, x2, y2, round(err, 3)])
        print(f"{a:6.2f}-{b:6.2f}: {seg[0]:.3f}->{seg[-1]:.3f} за {len(seg) - 1} кадров "
              f"({(len(seg) - 1) / FPS * 1000:.0f} мс)  cubic-bezier({x1}, {y1}, {x2}, {y2})  rmse {err:.3f}")
    with open(OUT / "easing_zoom.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_from", "t_to", "frames", "ms", "scale_from", "scale_to", "x1", "y1", "x2", "y2", "rmse"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
