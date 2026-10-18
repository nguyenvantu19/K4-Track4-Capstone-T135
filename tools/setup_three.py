"""Vendor a pinned, standalone Three.js ES module for offline local 3D."""
from pathlib import Path
from urllib.request import urlretrieve

destination = Path(__file__).resolve().parents[1] / "assets" / "vendor"
destination.mkdir(parents=True, exist_ok=True)
base = "https://raw.githubusercontent.com/mrdoob/three.js/r160/"
for remote, name in [("build/three.module.min.js", "three-r160.module.min.js"), ("LICENSE", "THREE-LICENSE.txt")]:
    path = destination / name
    if not path.exists():
        urlretrieve(base+remote, path)
    print(f"{name}: {path.stat().st_size} bytes")
