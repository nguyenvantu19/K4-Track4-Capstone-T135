"""Local webcam or video replay. Esc/Q exits. R resets.

Recording is explicit (--record); no raw media saved by default.
"""
import argparse
import csv
import time
from pathlib import Path
import cv2
from vinuni_move.core import Config, SquatCounter
from vinuni_move.vision import load_model, infer, annotate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or local video path")
    parser.add_argument("--side", choices=["left", "right"], default="left")
    parser.add_argument("--record", help="Explicit opt-in path for annotated backup MP4")
    parser.add_argument("--log", default="recordings/session.csv")
    args = parser.parse_args()
    model = load_model()
    camera = args.source.isdecimal()
    source = int(args.source) if camera else args.source
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise SystemExit("Khong mo duoc camera/video. Dong ung dung dang giu webcam hoac dung --source video.mp4")
    fps = capture.get(cv2.CAP_PROP_FPS)
    fps = fps if 1 <= fps <= 240 else 25.
    counter, writer = SquatCounter(), None
    rows, index, started = [], 0, time.perf_counter()
    print("Q/Esc: quit | R: reset counter | Raw video is not stored unless --record is set.")
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            t = time.perf_counter()-started if camera else index/fps
            before = time.perf_counter()
            image, angle, conf, count = infer(model, frame, args.side)
            row = counter.update(t, angle, conf, count)
            row["processing_ms"] = (time.perf_counter()-before)*1000
            rows.append(row)
            image = annotate(image, row)
            if args.record:
                if writer is None:
                    Path(args.record).parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(args.record, cv2.VideoWriter_fourcc(*"mp4v"), fps, (image.shape[1], image.shape[0]))
                    if not writer.isOpened():
                        raise RuntimeError("Cannot create recording")
                writer.write(image)
            cv2.imshow("VinUni Move - local webcam/video", image)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord("r"):
                counter = SquatCounter(Config())
            index += 1
    finally:
        capture.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        if rows:
            Path(args.log).parent.mkdir(parents=True, exist_ok=True)
            with open(args.log, "w", newline="", encoding="utf-8") as f:
                out = csv.DictWriter(f, fieldnames=rows[0].keys())
                out.writeheader()
                out.writerows(rows)
            print(f"Saved numerical log: {args.log}")


if __name__ == "__main__":
    main()
