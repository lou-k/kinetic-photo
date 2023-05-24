import argparse
import codecs
import json
import logging
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gphotospy.album import *

from integrations.common import Integration

service_name = "photoslibrary"
version = "v1"
scopes_arr = ["https://www.googleapis.com/auth/photoslibrary"]


class GooglePhotos(Integration):
    def __init__(self, **secrets):
        if "token" in secrets:
            self._token = pickle.loads(
                codecs.decode(secrets["token"].encode(), "base64")
            )
            del secrets["token"]
        else:
            self._token = None
        self._secrets = secrets
        self.__validate_token__()

    def __validate_token__(self):
        if not self._token or not self._token.valid:
            if self._token and self._token.expired and self._token.refresh_token:
                logging.debug("Refreshing google photos token...")
                self._token.refresh(Request())
            else:
                app_flow = InstalledAppFlow.from_client_config(
                    self._secrets, scopes_arr
                )
                # TODO : Switch this to a gui at somepoint..
                self._token = app_flow.run_local_server(port=9090)

    def params(self):
        rv = self._secrets
        if self._token:
            rv["token"] = codecs.encode(pickle.dumps(self._token), "base64").decode()
        return rv

    def __enter__(self):
        self.__validate_token__()
        service_object = {"secrets": self._secrets}
        service = build(
            service_name, version, static_discovery=False, credentials=self._token
        )
        service_object["service"] = service
        return service_object


if __name__ == "__main__":
    # gphotospy sends logging to a file and you can't change it :eyeroll:
    root = logging.getLogger()
    list(map(root.removeHandler, root.handlers))
    # Sets the logger format
    FORMAT = "%(asctime)s - %(levelname)s: %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Tests the google photos authorization"
    )
    parser.add_argument(
        "credentials", type=str, help="The credentials json file from google."
    )

    args = parser.parse_args()

    with open(args.credentials) as fin:
        credentials = json.load(fin)

    with GooglePhotos(**credentials) as gp:
        albums = Album(gp)
        for album in albums.list():
            logging.info(str(album))
            break
