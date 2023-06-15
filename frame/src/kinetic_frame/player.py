import argparse
import logging
import logging.config
import os
from subprocess import PIPE, STDOUT, Popen
from typing import List

from .config import DEFAULT_CONFIG_PATH, _load
from .photo_storage import *
import random
import time


def start_player(player_cmd: List[str], playlist_file: str):
    # TODO -- figure out how to pipe stderr and stdout to logging
    cmd = player_cmd + [playlist_file]
    return Popen(cmd, stderr=STDOUT)

def reset_playlist(frame: dict, client: KineticClient, storage_directory: str, playlist_file: str):
    version = frame['frame']['options'].get('preffered_version', 'original') if 'options' in frame['frame'] else 'original'
    object_ids = [c["versions"][version]  if version in c['versions'] else c['versions']['original'] for c in frame["content"]]
    object_ids = download_new_objects(client, object_ids, storage_directory)
    options = frame['frame']['options']
    if "shuffle" in options and options["shuffle"]:
        random.shuffle(object_ids)
    create_playlist(playlist_file, object_ids, storage_directory)
    delete_old_files(object_ids, storage_directory)

def stop_subprocess(sub):
    sub.terminate()
    sub.wait()

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
    playlist_file = config["playlist_file"]
    client = KineticClient(config["server"])

    os.makedirs(storage_directory, exist_ok=True)

    previous_frame = None
    frame = None
    subprocess_pid = None

    while True:
        logging.info(f"trying to get frame.. {frame_id}")
        try:
            frame = client.frame(frame_id)
        except Exception as e:
            if os.path.exists(playlist_file):
                logging.warning(f"Could not get frame id {frame_id}, proceeding with cached version of {playlist_file}...", exc_info=e)
                if not subprocess_pid:
                    subprocess_pid = start_player(config["player_cmd"], playlist_file)
            else:
                logging.error(f"Could not get frame id {frame_id}, trying again after {config['poll_interval']}ms...", exc_info=e)

        if frame and frame != previous_frame:
            previous_frame = frame        
            reset_playlist(previous_frame, client, storage_directory, playlist_file)
            if subprocess_pid:
                stop_subprocess(subprocess_pid)
            subprocess_pid = start_player(config["player_cmd"], playlist_file)
        try:
            time.sleep(config['poll_interval'])
        except KeyboardInterrupt as e:
            logging.warning(f"Caught iterrupt, exiting...")
            break
    stop_subprocess(subprocess_pid)


if __name__ == "__main__":
    main()
