import logging
import json
import subprocess
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple
from kinetic_server.common import Content, ContentVersion, Resolution

from kinetic_server.steps.step import ContentAugmentor


def get_video_time_data(filename: str) -> dict:
    """Retrieves info for a video file from on disk.

    Args:
        filename (str): The video file to get the time stats for.

    Returns:
        dict: A dictionary containing the video's frame rate, number of frames, and duration.
        Example:
         {
            "programs": [

            ],
            "streams": [
                {
                    "r_frame_rate": "30/1",
                    "nb_read_frames": "240"
                }
            ],
            "format": {
                "duration": "8.058000"
            }
        }
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-show_entries","format=duration","-v","error","-select_streams","v:0","-count_frames","-show_entries","stream=nb_read_frames,r_frame_rate","-print_format","json",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return json.loads(result.stdout)


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
    video_bytes: bytes,
    fade_duration: float = 1,
    video_bitrate: int = 1200,
    resolution: Optional[Resolution] = None
) -> Tuple[bytes, float]:
    """Adds a black fading effect to the beginning and ending of a video.

    Args:
        video_bytes (bytes): The video to alter
        fade_duration (float, optional): The number of seconds the fade shold be. Defaults to 1.
        video_bitrate (int, optional): The video bitrate (in k) for the re-encoded video. Defaults to 1200.
        resolution (Resolution, optional): Scale the video to the provided resolution

    Returns:
        Tuple[bytes, float]: The bytes of the re-rendered video, and the video duration.
    """
    with NamedTemporaryFile() as tmpfile:
        with open(tmpfile.name, "wb") as fout:
            fout.write(video_bytes)
        time_info = get_video_time_data(tmpfile.name)
        fps = eval(time_info['streams'][0]['r_frame_rate'])
        frames_to_fade = int(fade_duration * fps)
        total_frames = int(time_info['streams'][0]['nb_read_frames'])
        video_duration = float(time_info['format']['duration'])
        with NamedTemporaryFile(suffix=".mp4") as resultfile:
            cmd = [
                "ffmpeg",
                "-i",
                tmpfile.name,
                "-loglevel",
                "error",
                "-hide_banner",
                "-vf",
                f"fade=t=in:s=0:n={frames_to_fade},fade=t=out:s={total_frames - frames_to_fade}:n={frames_to_fade}"
            ]
            if resolution:
                cmd.extend([
                    "-vf",
                    f"scale={resolution.width}:{resolution.height}"
                ])

            cmd.extend([
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
            ])
            logging.info(f"Fading video with command:" + " ".join(cmd))
            subprocess.run(cmd, check=True)
            with open(resultfile.name, "rb") as fin:
                return (fin.read(), video_duration)


class Fade(ContentAugmentor):
    """Adds a fade to and from black at the beginning and end of the video clip. This makes transitions on frames a bit smoother.
    It will add a new video to the versions dictionary called "faded"
    """

    def __init__(self,
                 fade_duration: float = 1,
                 video_bitrate: int = 1200,
                 max_shortside_res: Optional[int] = None,
                 max_longside_res: Optional[int] = None):
        """Creates a new fade augmentor.

        Args:
            fade_duration (float, optional): The duration of the fade in seconds. Defaults to 1.
            video_bitrate (int, optional): The bitrate of the re-encoded video. Defaults to 1200.
            max_shortside_res (int, optional): The maximum resolution of the short side of the video.
            max_longside_res (int, optional): The maximum resolution of the long side of the video.
        """
        self.fade_duration = fade_duration
        self.video_bitrate = video_bitrate
        self.max_shortside_res = max_shortside_res
        self.max_longside_res = max_longside_res

    def augment(self, c: Content) -> Content:
        from ._apis import _object_store
        os = _object_store()

        if not ContentVersion.Faded in c.versions:
            logging.info(f"Generating faded video for content {c.id}...")
            try:

                # Get the target resolution (if needed)
                width, height = (c.resolution.width, c.resolution.height) if c.resolution else (None, None)
                scale = None
                if width and height:
                    longside = max(width, height)
                    shortside = min(width, height)
                    if self.max_longside_res and longside > self.max_longside_res:
                        scale = self.max_longside_res / float(longside)
                        shortside = int(scale * shortside)
                        logging.info(f"{self.max_longside_res} > {longside}, scale = {scale}")
                        
                    if self.max_shortside_res and shortside > self.max_shortside_res:
                        scale = scale if scale else 1.0
                        scale *= self.max_shortside_res / float(shortside)
                        logging.info(f"{self.max_shortside_res} > {shortside}, scale = {scale}")
                target_resolution = Resolution(int(width*scale), int(height*scale)) if scale else None
                if target_resolution:
                    logging.warn(f"Rescaling media {c.id} from {c.resolution.to_dict()} to {target_resolution.to_dict()}")
                else:
                    logging.info(f"Keeping original resolution for {c.id} of {c.resolution.to_dict()}")
                faded_bytes, video_duration = fade_video(
                    os.get_object_content(c.id),
                    video_bitrate=self.video_bitrate,
                    fade_duration=self.fade_duration,
                    resolution=target_resolution
                )
                c.versions[ContentVersion.Faded] = os.add_object(faded_bytes)
                c.metadata['duration'] = video_duration
            except Exception as e:
                logging.warning(f"Could not create faded video for {c.id}", exc_info=e)
                return c
        return c