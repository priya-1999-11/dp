from pathlib import Path
import time
from typing import Dict


def analyze_video(input_path: str, output_dir: str) -> Dict[str, str]:
    """
    Stub analyzer. Replace with your actual video analysis logic.

    It simulates work by sleeping and writes a small marker file to the
    per-video output directory to demonstrate concurrent-safe writes.
    """
    video = Path(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Simulate some CPU/IO work
    time.sleep(2)

    marker_file = out / "analysis.txt"
    marker_file.write_text(f"Analyzed: {video.name}\n")

    return {
        "video": video.name,
        "output_dir": str(out),
        "status": "ok",
    }

