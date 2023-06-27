import json

import requests


class KineticClient:
    def __init__(self, host: str, session: requests.Session = None):
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session
        self.host = host

    #
    # Abstractions over http requests
    #

    def __process_response__(self, resp):
        resp.raise_for_status()
        result = resp.text
        if not result:
            return {}
        else:
            return json.loads(result)

    def _get_json(self, path, params=None, **kwargs):
        return self.__process_response__(
            self.session.get(url=self.host + path, params=params, **kwargs)
        )

    def _put(self, path, data=None, **kwargs):
        return self.__process_response__(
            self.session.put(url=self.host + path, data=data, **kwargs)
        )

    #
    # Endpoints
    #

    def frame(self, id: str) -> dict:
        """Gets all of the frame info for the frame with the provided id.

        Args:
            id (str): The id of the frame to get.

        Returns:
            dict: An object containing the frame settings and content.
        """
        return self._get_json(f"/frame/{id}")

    def video(self, id: str) -> bytes:
        """Retrieves the video from the kinetic server.

        Args:
            id (str): The id of the video to download.

        Returns:
            bytes: An array of video bytes.
        """
        resp = self.session.get(url=f"{self.host}/video/{id}")
        resp.raise_for_status()
        return resp.content
    
    def download_video(self, id: str, filename: str) -> None:
        with self.session.get(url=f"{self.host}/video/{id}") as r:
            r.raise_for_status()
            with open(filename, 'wb') as fout:
                for chunk in r.iter_content(chunk_size=10*1024):
                    fout.write(chunk)