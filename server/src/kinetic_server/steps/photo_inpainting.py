import logging
from datetime import datetime
from typing import Optional, Union

from kinetic_server.common import Content, StreamMedia, get_resolution_and_orientation
from kinetic_server.steps.step import Step

from .gradio_clients import get as get_client


class PhotoInpainting(Step):
    """Renders a 3d inpainted video using "3D Photography using Context-aware Layered Depth Inpainting" by Shih et. al."""

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

    def __call__(self, media: Union[Content, StreamMedia]) -> Content:
        """Renders a 3d video of the provided media.

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
                f"PhotoInpainting can only be run for images, but stream media {media.identifier} was passed which is a video."
            )

        from ._apis import _content_api, _object_store

        os = _object_store()
        content_api = _content_api()

        if not ("mesh" in media.metadata and "depth_map" in media.metadata):
            raise Exception(
                f"A 3d mesh and a depth map are required for 3d photo inpainting, but {media.identifier} didn't have these..."
            )

        client = get_client(warmup=True, src=self.hf_src, hf_token=self.hf_token)
        depth_image_path = os._hash_path(media.metadata["depth_map"])
        mesh_path = os._hash_path(media.metadata["mesh"])

        logging.info(
            f"Rendering video for {media.identifier} using {self.hf_src}, this may take a while...."
        )
        start_t = datetime.now()

        result = client.predict(
            media.url, depth_image_path, mesh_path, api_name=self.hf_api_name
        )
        end_t = datetime.now()
        logging.info(
            f"Rendering the mesh for {media.identifier} took {str(end_t-start_t)}, result: {result}"
        )

        # Get the video orientation and resolution
        resolution, orientation = get_resolution_and_orientation(media)
        metadata = media.metadata
        if orientation:
            metadata["orientation"] = orientation.value

        # Create the new content
        with open(result, "rb") as fin:
            video_bytes = fin.read()
        os.remove(result)
        return content_api.create(
            video_file=video_bytes,
            resolution=resolution,
            created_at=media.created_at,
            source_id=media.identifier,
            stream_id=media.stream_id,
            metadata=metadata,
        )
