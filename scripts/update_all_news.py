from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "scripts" / "update_frontier_news.py",
    ROOT / "scripts" / "update_wechat_posts.py",
]


def main() -> int:
    code = 0
    for script in SCRIPTS:
        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
        if result.returncode != 0:
            code = result.returncode
    return code


if __name__ == "__main__":
    raise SystemExit(main())
