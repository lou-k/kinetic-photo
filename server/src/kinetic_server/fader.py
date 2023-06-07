import logging
import subprocess
from tempfile import NamedTemporaryFile
from typing import Tuple


def get_video_duration(filename: str) -> float:
    """Retrieves the duration of a video file on disk

    Args:
        filename (str): The video file to compute the duration for.

    Returns:
        float: The duration of the video in seconds
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return float(result.stdout)


def fade_video(
    video_bytes: bytes, fade_duration: float = 1, video_bitrate: int = 1200
) -> Tuple[bytes, float]:
    """Adds a black fading effect to the beginning and ending of a video.

    Args:
        video_bytes (bytes): The video to alter
        fade_duration (float, optional): The number of seconds the fade shold be. Defaults to 1.
        video_bitrate (int, optional): The video bitrate (in k) for the re-encoded video. Defaults to 1200.

    Returns:
        Tuple[bytes, float]: The bytes of the re-rendered video, and the video duration.
    """
    with NamedTemporaryFile() as tmpfile:
        with open(tmpfile.name, "wb") as fout:
            fout.write(video_bytes)
        video_duration = get_video_duration(tmpfile.name)
        with NamedTemporaryFile(suffix=".mp4") as resultfile:
            cmd = [
                "ffmpeg",
                "-i",
                tmpfile.name,
                "-vf",
                f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={video_duration - fade_duration}:d={fade_duration}",
                "-b:v",
                f"{video_bitrate}k",
                "-c:a",
                "copy",
                "-f",
                "mp4",
                "-movflags",
                "+faststart",
                "-y",
                resultfile.name,
            ]
            logging.info(f"Fading video with command:" + " ".join(cmd))
            subprocess.run(cmd, check=True)
            with open(resultfile.name, "rb") as fin:
                return (fin.read(), video_duration)
