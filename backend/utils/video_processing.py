"""
動画処理ユーティリティ

ffmpeg/ffprobeをサブプロセスとして呼び出し、動画のメタデータ取得・
位置情報等メタデータの除去・サムネイル用フレーム抽出を行う。

方針:
- 動画本体の再エンコードは行わない（Raspberry Piへの負荷を避けるため）。
  メタデータ除去はストリームコピー（-c copy）で実施する。
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

FFPROBE_TIMEOUT_SECONDS = 15
FFMPEG_TIMEOUT_SECONDS = 60


class VideoProcessingError(Exception):
    """動画処理（ffprobe/ffmpeg呼び出し）に失敗した場合の例外"""
    pass


class VideoProbeResult(TypedDict):
    duration_seconds: Optional[float]
    width: Optional[int]
    height: Optional[int]
    creation_time: Optional[str]
    has_video_stream: bool


def probe_video(path: Path) -> VideoProbeResult:
    """
    ffprobeで動画のメタデータ（長さ・解像度・撮影日時）を取得する。

    Raises:
        VideoProcessingError: ffprobeの実行に失敗、または出力の解析に失敗した場合
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        raise VideoProcessingError(f"ffprobe execution failed: {e}")

    if result.returncode != 0:
        raise VideoProcessingError(f"ffprobe failed: {result.stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise VideoProcessingError(f"Failed to parse ffprobe output: {e}")

    format_info = data.get("format", {})
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

    duration_raw = format_info.get("duration")
    duration_seconds = float(duration_raw) if duration_raw is not None else None

    return VideoProbeResult(
        duration_seconds=duration_seconds,
        width=video_stream.get("width") if video_stream else None,
        height=video_stream.get("height") if video_stream else None,
        creation_time=format_info.get("tags", {}).get("creation_time"),
        has_video_stream=video_stream is not None,
    )


def strip_metadata_and_copy(input_path: Path, output_path: Path) -> None:
    """
    メタデータ（位置情報等）を除去して動画をコピーする。
    映像・音声ストリームは再エンコードしない（-c copy）。

    Raises:
        VideoProcessingError: ffmpegの実行に失敗した場合
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-map_metadata", "-1",
        "-c", "copy",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        raise VideoProcessingError(f"ffmpeg metadata strip failed: {e}")

    if result.returncode != 0:
        raise VideoProcessingError(f"ffmpeg metadata strip failed: {result.stderr}")


def extract_thumbnail_frame(video_path: Path, output_path: Path) -> None:
    """
    動画から1フレームを静止画として抽出する（サムネイル生成用）。

    Raises:
        VideoProcessingError: ffmpegの実行に失敗した場合
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", "00:00:00.5",
        "-i", str(video_path),
        "-vframes", "1",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        raise VideoProcessingError(f"ffmpeg thumbnail extraction failed: {e}")

    if result.returncode != 0:
        raise VideoProcessingError(f"ffmpeg thumbnail extraction failed: {result.stderr}")
