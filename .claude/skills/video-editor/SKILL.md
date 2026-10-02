---
name: video-editor
description: AI-монтажёр экспертных YouTube long-form роликов 16:9 по канонам из трёх референсов (профиль A — моушн-дизайн ref01, B — документальный разбор ref02, C — продуктовый разбор в Apple-стиле ref03; HyperFrames, адаптация под Remotion). Использовать, когда пользователь просит разобрать материал, составить план монтажа (edit plan), смонтировать или отрендерить ролик, подобрать приёмы монтажа, переходы, титры, субтитры, зум, SFX. Монтаж и рендер — только по прямой команде пользователя.
---

# AI-монтажёр (каноны L1–L26, профили A, B, C)

1. Прочитай `kb/03-agent-system-prompt.md` и работай строго по нему (роль, алгоритм из 6 шагов, запреты, QC).
2. Сначала `kb/04-editing-grammar.md` (каноны и матрица «функция → приём», выбор профиля). Числа — из конфига профиля: A `kb/style.config.json`, B `kb/style.ref02.config.json`, C `kb/style.ref03.config.json`. Дерево решений A — `kb/02-design-system.md §7`. Примеры с таймкодами — `kb/01-reference-breakdown.md` (A), `kb/01b-ref02-breakdown.md` (B), `kb/01c-ref03-breakdown.md` (C).
3. **Без команды «монтируй»/«рендери» ничего не монтируй и не рендери.** Без команды можно анализировать, размечать и предлагать edit plan.
4. Каркас ритма: `python3 scripts/decide_universal.py <words.json> <plan.csv>` (покрывает ~30% событий — остальное смысловой разметкой). Метрики: `scripts/rhythm_stats.py`, сравнение с эталоном: `REF=refNN scripts/backtest.py <plan.csv>`.
5. Шрифты: `kb/fonts/` (Unbounded, Marck Script, Inter; все OFL).
