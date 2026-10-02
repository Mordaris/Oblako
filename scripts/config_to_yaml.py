"""kb/style.config.json -> kb/style.config.yaml (YAML — производный файл, правится только JSON)."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "kb" / "style.config.json").read_text(encoding="utf-8"))
hdr = "# Сгенерировано из kb/style.config.json (python3 scripts/config_to_yaml.py). Править JSON, не этот файл.\n"
(ROOT / "kb" / "style.config.yaml").write_text(hdr + yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=120),
                                               encoding="utf-8")
