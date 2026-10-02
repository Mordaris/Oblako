"""Подбор cubic-bezier(x1,y1,x2,y2) по покадровым значениям анимируемого параметра.

Использование как модуль: fit(values) -> (x1, y1, x2, y2, rmse)
Запуск: python3 scripts/fit_easing.py  — фит всех зум-рампов из analysis/zoom.csv,
         результат: analysis/easing_zoom.csv
"""
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
FPS = 2997 / 100


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
    z = list(csv.DictReader(open(ROOT / "analysis" / "zoom.csv")))
    sc = np.array([float(r["scale"]) if r["scale"] else np.nan for r in z])
    # рампы из анализа Фазы 2: (начало, конец) в секундах, с запасом по 2 кадра
    ramps = [(0.80, 1.65), (23.45, 24.20), (30.98, 31.95), (51.28, 52.08), (53.30, 54.45), (66.15, 67.12),
             (75.46, 76.30), (77.42, 78.64), (86.00, 86.88)]
    rows = []
    for a, b in ramps:
        seg = sc[int(a * FPS):int(b * FPS) + 1]
        seg = seg[~np.isnan(seg)]
        # обрезать плато: от первого кадра изменения до последнего
        d = np.abs(np.diff(seg))
        on = np.where(d > 0.0015)[0]
        seg = seg[on[0]:on[-1] + 2]
        x1, y1, x2, y2, err = fit(seg)
        rows.append([a, b, len(seg) - 1, round((len(seg) - 1) / FPS * 1000), round(seg[0], 3), round(seg[-1], 3),
                     x1, y1, x2, y2, round(err, 3)])
        print(f"{a:6.2f}-{b:6.2f}: {seg[0]:.3f}->{seg[-1]:.3f} за {len(seg) - 1} кадров "
              f"({(len(seg) - 1) / FPS * 1000:.0f} мс)  cubic-bezier({x1}, {y1}, {x2}, {y2})  rmse {err:.3f}")
    with open(ROOT / "analysis" / "easing_zoom.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_from", "t_to", "frames", "ms", "scale_from", "scale_to", "x1", "y1", "x2", "y2", "rmse"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
