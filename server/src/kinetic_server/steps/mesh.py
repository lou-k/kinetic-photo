import logging
import os
from datetime import datetime
from typing import Optional, Union

from kinetic_server.common import Content, StreamMedia
from kinetic_server.steps.step import Step

from .gradio_clients import get as get_client

MESH_TYPE = "mesh"


class ComputeMesh(Step):
    """Extracts or computes a mesh map for the provided image and stores it in the mesh cache."""

    def __init__(
        self,
        hf_src: Optional[str],
        hf_token: Optional[str],
        hf_api_name: str = "/predict",
    ):
        """Creates a new mesh extractor

                Args:
                    hf_src (Optional[str]): Either the name of the Hugging Face Space to load, (e.g. "abidlabs/whisper-large-v2") or the full URL (including "http" or "https") of the hosted Gradio app to load (e.g. "http://mydomain.
        com/app" or "https://bec81a83-5b5c-471e.gradio.live/") of the gradio app that computes mesges from images and depth maps.
                    hf_token (Optional[str]):  The Hugging Face token to use to access private Spaces. Automatically fetched if you are logged in via the Hugging Face Hub CLI. Obtain from: https://huggingface.co/settings/token
                    hf_api_name (str): The api name of the hugging face call (usually "/predict")
        """
        self.hf_src = hf_src
        self.hf_token = hf_token
        self.hf_api_name = hf_api_name

    def __call__(self, media: Union[Content, StreamMedia]) -> StreamMedia:
        """Computes a 3d mesh for the image in the provided media.
        If a Content is passed, an exception is thrown.
        If the media does not have a depth map in it's metadata, an exception is thrown.

        Args:
            media (StreamMedia): The media to generate a mesh map from.

        Returns:
            If successful, a StreamMedia with metadata['mesh'] set to it's hashed image file.
            If not successful, the input StreamMedia.
        """
        if type(media) != StreamMedia:
            raise Exception(
                f"ComputeMesh requires a StreamMedia but {str(type(media))} was passed."
            )
        if media.is_video:
            raise Exception(
                f"Mesh can only be extracted for images, but stream media {media.identifier} was passed which is a video."
            )

        from ._apis import _auxiliary_cache

        auxiliary_cache = _auxiliary_cache()

        # See if this image already has a mesh image
        mesh = auxiliary_cache.db.get(media.identifier, type=MESH_TYPE)
        if mesh:
            logging.info(f"{media.identifier} already hash mesh {mesh.file_hash}!")
        else:
            # Compute the mesh image
            logging.info(
                f"Computing mesh for {media.identifier} using {self.hf_src}, this may take a while...."
            )
            if "depth_map" not in media.metadata:
                raise Exception(f"Media {media.identifier} has no depth map...")
            depth_image_path = auxiliary_cache.os._hash_path(media.metadata["depth_map"])
            start_t = datetime.now()
            client = get_client(src=self.hf_src, hf_token=self.hf_token)
            result = client.predict(
                media.url, depth_image_path, api_name=self.hf_api_name
            )
            end_t = datetime.now()
            logging.info(
                f"Computing the mesh for {media.identifier} took {str(end_t-start_t)}, result: {result}"
            )

            with open(result, "rb") as fin:
                mesh_bytes = fin.read()
            mesh = auxiliary_cache.save(media.identifier, MESH_TYPE, mesh_bytes)
            os.remove(result)

        media.metadata["mesh"] = mesh.file_hash
        return media
