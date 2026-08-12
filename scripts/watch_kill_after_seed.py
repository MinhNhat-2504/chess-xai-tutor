"""Watch a benchmark output marker and stop a process when it appears."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import signal
import time
from pathlib import Path


def write_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--marker-dir", required=True)
    ap.add_argument("--marker-file")
    ap.add_argument("--log", required=True)
    ap.add_argument("--interval", type=float, default=30.0)
    args = ap.parse_args()

    marker_dir = Path(args.marker_dir)
    marker_file = Path(args.marker_file) if args.marker_file else None
    log_path = Path(args.log)

    write_log(log_path, f"watcher started for PID {args.pid}")
    while process_exists(args.pid):
        if marker_dir.exists() or (marker_file is not None and marker_file.exists()):
            write_log(log_path, f"marker detected ({marker_dir}); sending SIGTERM to PID {args.pid}")
            try:
                os.kill(args.pid, signal.SIGTERM)
            except ProcessLookupError:
                write_log(log_path, f"PID {args.pid} already exited")
                return
            time.sleep(2.0)
            if process_exists(args.pid):
                write_log(log_path, f"PID {args.pid} still alive; sending SIGKILL")
                try:
                    os.kill(args.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return
        time.sleep(args.interval)

    write_log(log_path, f"PID {args.pid} ended before marker detection")


if __name__ == "__main__":
    main()
