"""Generate all book figures into chapters/images/.

    python3 scripts/figures/build.py          # all
    python3 scripts/figures/build.py fig-09   # only names starting with fig-09
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import figs_core  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "chapters" / "images"
MODULES = [figs_core]
for name in ("figs_more", "figs_platform"):
    try:
        MODULES.append(__import__(name))
    except ModuleNotFoundError:
        pass


def main() -> None:
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    for mod in MODULES:
        for name, make in mod.FIGS.items():
            if not name.startswith(prefix):
                continue
            fig = make()
            (OUT / f"{name}.svg").write_text(fig.svg(), encoding="utf-8")
            status = "  WARN " + "; ".join(fig.warnings) if fig.warnings else ""
            print(f"{name}.svg{status}")


if __name__ == "__main__":
    main()
