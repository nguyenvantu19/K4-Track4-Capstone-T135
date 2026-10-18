"""Export an offline, standalone HTML version of the 3D simulator."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vinuni_move.viewer3d import document

if __name__ == "__main__":
    out = ROOT / "outputs" / "vinuni-move-3d.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(document(), encoding="utf-8")
    print(out)
