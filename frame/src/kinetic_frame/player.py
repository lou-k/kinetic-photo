import argparse
import logging
import logging.config
import os
from subprocess import PIPE, STDOUT, Popen
from typing import List

from .config import DEFAULT_CONFIG_PATH, _load
from .photo_storage import *


def start_player(player_cmd: List[str], playlist_file: str):
    # TODO -- figure out how to pipe stderr and stdout to logging
    cmd = player_cmd + [playlist_file]
    return Popen(cmd, stderr=STDOUT)


def main():
    logging.config.fileConfig(
        fname=os.path.join(os.path.dirname(__file__), "logging.ini")
    )

    parser = argparse.ArgumentParser(
        prog="kinetic-frame", description="Displays kinetic photos on your frame"
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="A path to the config file.",
        default=DEFAULT_CONFIG_PATH,
    )
    parser.add_argument(
        "-f",
        "--frame",
        type=str,
        help="The frame id to start with (overrides the config setting).",
        default=None,
    )

    args = parser.parse_args()
    config = _load(args.config)

    frame_id = args.frame if args.frame else config["frame_id"]
    storage_directory = config["storage_directory"]
    os.makedirs(storage_directory, exist_ok=True)
    playlist_file = config["playlist_file"]
    client = KineticClient(config["server"])

    frame = client.frame(frame_id)
    object_ids = [c["id"] for c in frame["content"]]
    kept_ids = download_new_objects(client, object_ids, storage_directory)
    create_vlc_playlist(playlist_file, kept_ids, storage_directory)
    delete_old_files(kept_ids, storage_directory)
    subprocess_pid = start_player(config["player_cmd"], playlist_file)
    subprocess_pid.wait()


if __name__ == "__main__":
    main()
