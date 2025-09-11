import argparse
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# Import the user's analyzer. Replace the implementation in analysis.py with your real logic.
try:
    from analysis import analyze_video  # type: ignore
except Exception as import_error:  # pragma: no cover
    print("Failed to import analyze_video from analysis.py. Make sure analysis.py exists and defines analyze_video(input_path: str, output_dir: str) -> dict.")
    raise


SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".m4v",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze multiple videos concurrently from a selected folder.",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing input videos.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=False,
        default="./analysis_outputs",
        help="Root directory where per-video outputs will be written.",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=",".join(sorted(SUPPORTED_EXTENSIONS)),
        help="Comma-separated list of file extensions to include (e.g. .mp4,.mov).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search input directory recursively.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) // 2),
        help="Maximum number of videos to analyze in parallel (processes).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of videos to process (0 means no limit).",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential processing (useful for debugging).",
    )
    return parser.parse_args(argv)


def find_videos(input_dir: Path, extensions: Iterable[str], recursive: bool) -> List[Path]:
    normalized_exts = {ext.lower().strip() for ext in extensions}
    if recursive:
        candidates = [p for p in input_dir.rglob("*") if p.is_file()]
    else:
        candidates = [p for p in input_dir.glob("*") if p.is_file()]
    videos: List[Path] = []
    for path in candidates:
        if path.suffix.lower() in normalized_exts:
            videos.append(path)
    videos.sort()
    return videos


def per_video_output_dir(output_root: Path, video_path: Path) -> Path:
    safe_stem = video_path.stem
    # Create a subfolder per video to avoid write conflicts
    return output_root / safe_stem


def worker(video_path: str, output_root: str) -> Tuple[str, str, dict]:
    """Run analyze_video on a single input. Returns (input_path, output_dir, result_dict)."""
    input_path = Path(video_path)
    root = Path(output_root)
    out_dir = per_video_output_dir(root, input_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict = analyze_video(str(input_path), str(out_dir))
    return (str(input_path), str(out_dir), result)


def run_sequential(videos: List[Path], output_root: Path) -> None:
    for idx, video in enumerate(videos, start=1):
        print(f"[{idx}/{len(videos)}] Analyzing: {video}")
        try:
            input_path, out_dir, result = worker(str(video), str(output_root))
            print(f"✔ Done: {input_path} -> {out_dir}")
            if result:
                print(f"  Result: {result}")
        except Exception as exc:  # pragma: no cover
            print(f"✖ Failed: {video}\n{exc}")
            traceback.print_exc()


def run_parallel(videos: List[Path], output_root: Path, max_workers: int) -> None:
    max_workers = max(1, max_workers)
    print(f"Starting parallel analysis with {max_workers} workers for {len(videos)} videos...")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_video = {
            executor.submit(worker, str(video), str(output_root)): str(video)
            for video in videos
        }
        completed = 0
        total = len(future_to_video)
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            completed += 1
            try:
                input_path, out_dir, result = future.result()
                print(f"[{completed}/{total}] ✔ Done: {input_path} -> {out_dir}")
                if result:
                    print(f"  Result: {result}")
            except Exception as exc:  # pragma: no cover
                print(f"[{completed}/{total}] ✖ Failed: {video}\n{exc}")
                traceback.print_exc()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    output_root = Path(args.output_dir)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory not found or not a directory: {input_dir}")
        return 2
    output_root.mkdir(parents=True, exist_ok=True)

    extensions = [e.strip() for e in args.extensions.split(",") if e.strip()]
    videos = find_videos(input_dir, extensions, args.recursive)
    if args.limit and args.limit > 0:
        videos = videos[: args.limit]

    if not videos:
        print("No videos found. Supported extensions:", ", ".join(extensions))
        return 0

    print(f"Found {len(videos)} videos in {input_dir}")
    print("Processing mode:", "sequential" if args.sequential else f"parallel x{max(1, args.max_workers)}")

    if args.sequential:
        run_sequential(videos, output_root)
    else:
        run_parallel(videos, output_root, args.max_workers)

    print("All tasks finished.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

