import logging
import os
import subprocess
import sys
from tempfile import NamedTemporaryFile
from typing import List

from .common import ContentVersion, PreRender
from .db import PreRenderDb
from .frames import FramesApi
from .object_store import ObjectStore


class PreRenderApi:
    def __init__(self, db: PreRenderDb, os: ObjectStore, frames_api: FramesApi):
        self.db = db
        self.os = os
        self.frames_api = frames_api

    def _create_video(
        self, paths: List[str], width: int, height: int, video_bitrate: int
    ) -> bytes:
        width = str(width)
        height = str(height)
        with NamedTemporaryFile(suffix="playlist.txt") as tmpfile:
            with open(tmpfile.name, "w") as fout:
                for p in paths:
                    fout.write(f"file '{os.path.abspath(p)}'\n")
            with NamedTemporaryFile(suffix=".mp4") as resultfile:
                filter = (
                    "scale=iw*min("
                    + width
                    + "/iw\,"
                    + height
                    + "/ih):ih*min("
                    + width
                    + "/iw\,"
                    + height
                    + "/ih),pad="
                    + width
                    + ":"
                    + height
                    + ":("
                    + width
                    + "-iw*min("
                    + width
                    + "/iw\,"
                    + height
                    + "/ih))/2:("
                    + height
                    + "-ih*min("
                    + width
                    + "/iw\,"
                    + height
                    + "/ih))/2"
                )
                subprocess.call(["cat", f"{tmpfile.name}"])
                cmd = [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    tmpfile.name,
                    "-loglevel",
                    "error",
                    "-hide_banner",
                    "-vf",
                    filter,
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
                logging.info(f"Building video with command:" + " ".join(cmd))
                subprocess.run(cmd, check=True)
                with open(resultfile.name, "rb") as fin:
                    return fin.read()

    def render_if_necessary(
        self,
        frame_id: str,
        width: int = 1920,
        height: int = 1080,
        video_bitrate: int = 1200,
    ) -> PreRender:
        # Load the video ids previously used
        last_render = self.db.get_for_frame(frame_id, 1)
        last_videos = last_render[0].video_ids if len(last_render) else []

        # Get the video ids list of the frame
        frame = self.frames_api.get(frame_id)
        content = self.frames_api.get_content_for(frame_id, sys.maxsize)
        preffered_version = (
            frame.options["preffered_version"]
            if "preffered_version" in frame.options
            else ContentVersion.Original
        )
        video_ids = [c.versions.get(preffered_version, c.id) for c in content]
        logging.info(f"There are {len(video_ids)} kinetic photos for frame {frame_id}")

        if video_ids == last_videos:
            logging.info(
                f"Existing pre-render {last_render[0].id} {last_render[0].video_hash} is up to date."
            )
            return last_render[0]
        else:
            logging.info(f"Rendering video for frame {frame_id}")
            paths = [self.os._hash_path(id) for id in video_ids]
            video_bytes = self._create_video(paths, width, height, video_bitrate)
            video_hash = self.os.add(video_bytes)
            return self.db.create(frame_id, video_hash=video_hash, video_ids=video_ids)
