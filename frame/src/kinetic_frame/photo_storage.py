import glob
import logging
import os
from typing import Iterable, Set

from tqdm import tqdm

from .client import KineticClient


def download_video(client: KineticClient, id: str, directory: str) -> bool:
    """Caches the video to the provided directory.

    Args:
        client (KineticClient): The kinetic photos client
        id (str): The id of the video to download
        directory (str): Where to store the resulting video

    Returns:
        bool: True if the video was successfully downloaded, false otherwise.
    """
    try:
        bytes = client.video(id)
        filename = os.path.join(directory, id)
        with open(filename, "wb") as fout:
            fout.write(bytes)
        return True
    except Exception as e:
        logging.error(f"Could not download video {id}", e)
        return False


def list_objects_on_disk(directory: str) -> Set[str]:
    return set([os.path.basename(i) for i in glob.glob(os.path.join(directory, "*"))])


def download_new_objects(
    client: KineticClient, ids: Iterable[str], directory: str
) -> Set[str]:
    """Downloads the kinetic photos (i.e., video files) to {{directory}}.

    Args:
        client (KineticClient): A client for the kinetic photos server
        ids: (Set[str]): the identifiers of the photos to download
        directory (str): Where to store them

    Returns:
        Set[str]: The identifiers that were successfully downloaded.
    """
    on_disk = list_objects_on_disk(directory)
    to_download = set(ids) - on_disk
    logging.info(f"There are {len(to_download)} photos to download.")
    kept = []
    for id in tqdm(to_download, total=len(to_download)):
        if download_video(client, id, directory):
            kept.append(id)
    logging.info(f"Successfully downloaded {len(kept)}/{len(to_download)} photos.")
    kept = set(kept)

    result = kept.union(set(ids).intersection(on_disk))
    
    # keep the original order of the input ids
    return [i for i in ids if i in result]


def delete_old_files(ids_to_keep: Set[str], directory: str) -> None:
    """Deletes any files in {{directory}} that are not in {{ids_to_keep}}

    Args:
        ids_to_keep (Set[str]): object identifiers to keep.
        directory (str): storage directory
    """
    ids_to_keep = set(ids_to_keep)
    on_disk = list_objects_on_disk(directory)
    to_delete = on_disk - ids_to_keep
    logging.info(f"{len(to_delete)} photos will be deleted.")
    for id in to_delete:
        os.remove(os.path.join(directory, id))


def create_playlist(filename: str, object_ids: Set[str], directory: str) -> None:
    """Generates a playlist file for vlc containing all of the kinetic
    photos in {{object_ids}}

    Args:
        filename (str): Where to write the playlist file.
        object_ids (Set[str]): The photo identifiers to include.
        directory (str): Where the photos are stored.
    """
    with open(filename, "w") as fout:
        fout.writelines([os.path.join(directory, id) + "\n" for id in object_ids])
