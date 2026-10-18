"""Start the local UI with the current Python environment and open a browser."""
import argparse
import importlib.util
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def find_port(preferred):
    for port in range(preferred, min(preferred+10, 65536)):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free local port. Close an older app or choose --port.")


def main():
    parser = argparse.ArgumentParser(description="VinUni Move local UI")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check dependencies without opening a camera or starting a server")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65525:
        parser.error("Use a port between 1024 and 65525")
    missing = [name for name in ("streamlit", "cv2", "numpy", "pandas", "ultralytics") if importlib.util.find_spec(name) is None]
    if missing:
        print("Missing dependencies: " + ", ".join(missing))
        print(f'Run: "{sys.executable}" -m pip install -r requirements.txt')
        return 1
    if args.check:
        print("Local UI dependencies: OK")
        print("Pose model: " + ("ready" if (ROOT/"models"/"yolo11n-pose.pt").exists() else "not downloaded; simulation remains available"))
        return 0
    port = find_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"VinUni Move: {url}\nPress Ctrl+C to stop. No camera opens automatically.", flush=True)
    process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT/"app.py"), "--server.address", "127.0.0.1", "--server.port", str(port), "--server.headless", "true", "--browser.gatherUsageStats", "false"], cwd=ROOT)
    done = threading.Event()

    def open_when_ready():
        for _ in range(60):
            if done.is_set() or process.poll() is not None:
                return
            try:
                with urlopen(url+"/_stcore/health", timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except OSError:
                done.wait(.5)

    if not args.no_browser:
        threading.Thread(target=open_when_ready, daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping VinUni Move…", flush=True)
        return 0
    finally:
        done.set()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
