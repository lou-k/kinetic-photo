import logging
import os
from datetime import datetime
from typing import Optional, Union

from kinetic_server.common import Content, StreamMedia
from kinetic_server.steps.step import Step

from .gradio_clients import get as get_client

DEPTH_TYPE = "depth"


class ComputeDepth(Step):
    """Extracts or computes a depth map for the provided image and stores it in the depth cache."""

    def __init__(
        self,
        hf_src: Optional[str],
        hf_token: Optional[str],
        hf_api_name: str = "/predict",
    ):
        """Creates a new depth extractor

                Args:
                    hf_src (Optional[str]): Either the name of the Hugging Face Space to load, (e.g. "abidlabs/whisper-large-v2") or the full URL (including "http" or "https") of the hosted Gradio app to load (e.g. "http://mydomain.
        com/app" or "https://bec81a83-5b5c-471e.gradio.live/") of the gradio app that computes depth maps from images.
                    hf_token (Optional[str]):  The Hugging Face token to use to access private Spaces. Automatically fetched if you are logged in via the Hugging Face Hub CLI. Obtain from: https://huggingface.co/settings/token
                    ht_api_name (str): The api endpoint name of the hugginface app (usually "/predict" or "/predic_1" etc)
        """
        self.hf_src = hf_src
        self.hf_token = hf_token
        self.hf_api_name = hf_api_name

    def __call__(self, media: Union[Content, StreamMedia]) -> StreamMedia:
        """Computes the depth map for the image in the provided media.
        If a Content is passed, an exception is thrown.

        Args:
            media (StreamMedia): The media to generate a depth map from.

        Returns:
            If successful, a StreamMedia with metadata['depth'] set to it's hashed image file.
            If not successful, the input StreamMedia.
        """
        if type(media) != StreamMedia:
            raise Exception(
                f"ComputeDepth requires a StreamMedia but {str(type(media))} was passed."
            )
        if media.is_video:
            raise Exception(
                f"Depth can only be extracted for images, but stream media {media.identifier} was passed which is a video."
            )

        from ._apis import _auxiliary_cache

        auxiliary_cache = _auxiliary_cache()

        # See if this image already has a depth image
        depth_image = auxiliary_cache.db.get(media.identifier, type=DEPTH_TYPE)
        if depth_image:
            logging.info(f"{media.identifier} has depth image {depth_image.file_hash}")
        else:
            # Compute the depth image
            try:
                logging.info(
                    f"Extracting depth for {media.identifier} using {self.hf_src}, this may take a while...."
                )
                start_t = datetime.now()
                client = get_client(src=self.hf_src, hf_token=self.hf_token)
                result = client.predict(media.url, api_name=self.hf_api_name)
                end_t = datetime.now()
                logging.info(
                    f"Computing the depth map for {media.identifier} took {str(end_t-start_t)}, result: {result}"
                )

                if len(result) > 1 and result[1] == "Completed":
                    with open(result[0], "rb") as fin:
                        depth_bytes = fin.read()
                    depth_image = auxiliary_cache.save(
                        media.identifier, DEPTH_TYPE, depth_bytes
                    )
                    os.remove(result[0])
                else:
                    raise Exception(f"Depth computation failed with result {result}")
            except Exception as e:
                logging.warning(
                    f"Could not compute depth for {media.identifier}:", exc_info=e
                )
                return media

        media.metadata["depth_map"] = depth_image.file_hash
        return media
