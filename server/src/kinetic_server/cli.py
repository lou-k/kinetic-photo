"""
Provides a command line interface (CLI) for managing content in kinetic photo server

"""
import argparse
import itertools
import json
import logging
import sys

import tqdm
from dependency_injector.wiring import Provide, inject

from .containers import Container
from .frames import FramesApi
from .integrations import IntegrationsApi, IntegrationType
from .object_store import ObjectStore
from .pipelines import PipelineApi
from .pre_renders import PreRenderApi
from .steps import list_steps
from .streams import StreamsApi, StreamType
from .uploads import UploadsApi


@inject
def streams(
    args,
    streams_api: StreamsApi = Provide[Container.streams_api],
) -> None:
    def show_head(id, n):
        stream = streams_api.get(id=id)
        logging.info(f"First {n} items in stream {id}:")
        for i in itertools.islice(stream, n):
            logging.info(i.to_json())

    match args.action:
        case "list":
            integrations = streams_api.list()
            logging.info(integrations)
        case "remove":
            streams_api.remove(id=args.id)
        case "add":
            with open(args.params_file) as fin:
                params = json.load(fin)
            # Ensure we have an intgeration id if needed
            typ = StreamType[args.type]
            if (
                typ
                in set(
                    [StreamType.Google_Photos_Album, StreamType.Google_Photos_Search]
                )
                and not args.integration
            ):
                raise Exception(
                    f"An intgration id must be set when creating streams of type {typ.name}"
                )

            stream_id = streams_api.add(
                name=args.name, typ=typ, integration_id=args.integration, params=params
            )
            logging.info(f'Created stream {stream_id} with name "{args.name}"')
            show_head(stream_id, 5)
        case "head":
            show_head(args.id, args.n)


def streams_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(name="streams", help="Manage media streams")

    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(name="add", help="Add a stream")
    add_parser.add_argument(
        "params_file",
        help="A json file of arguments to the stream",
        type=str,
    )
    add_parser.add_argument("name", help="What to name this stream")
    add_parser.add_argument(
        "type",
        help="The type of stream to store",
        choices=[t.name for t in StreamType],
        type=str,
    )
    add_parser.add_argument(
        "-i",
        "--integration",
        help="The integration id for this stream (if needed -- required for google photos)",
        type=int,
    )
    add_parser.set_defaults(action="add")

    remove_parser = subparsers.add_parser(name="remove", help="Removes a stream")
    remove_parser.set_defaults(action="remove")
    remove_parser.add_argument("id", help="The id of the stream to remove")

    list_parser = subparsers.add_parser(name="list", help="Show existing streams")
    list_parser.set_defaults(action="list")

    head_parser = subparsers.add_parser(
        name="head", help="Displays the first few items in a stream"
    )
    head_parser.set_defaults(action="head")
    head_parser.add_argument("id", help="The id of the stream to show.", type=int)
    head_parser.add_argument(
        "-n", help="The number of items to show.", type=int, default=5
    )

    parser.set_defaults(func=streams)


@inject
def integrations(
    args,
    integrations_api: IntegrationsApi = Provide[Container.integrations_api],
) -> None:
    match args.action:
        case "list":
            integrations = integrations_api.list()
            logging.info(integrations)
        case "remove":
            integrations_api.remove(id=args.id)
        case "add":
            # parse the integration parameters
            with open(args.params_file) as fin:
                params = json.load(fin)

            # Create the integration
            typ = IntegrationType[args.type]
            integration = integrations_api.from_params(typ, params)

            # Confirm it works
            with integration as api:
                logging.info("Integration initialized")
            # Store them in the database
            integration_id = integrations_api.add(args.name, integration)
            logging.info(f"Stored a new integration with id {integration_id}")

            # load them back to ensure they worked properly
            integration = integrations_api.get(integration_id)
            with integration as api:
                logging.info("Integration api loaded sucessfully.")


def integrations_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(
        name="integrations", help="Manage external integrations"
    )

    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(name="add", help="Add an integration")
    add_parser.add_argument(
        "params_file", help="The filename to load the parmaters from", type=str
    )
    add_parser.add_argument("name", help="What to name this integrations")
    add_parser.add_argument(
        "type",
        help="The type of integrations to store",
        choices=[t.name for t in IntegrationType],
        type=str,
    )
    add_parser.set_defaults(action="add")

    remove_parser = subparsers.add_parser(name="remove", help="Remove an integration")
    remove_parser.set_defaults(action="remove")
    remove_parser.add_argument("id", help="The id of the integration to remove")

    list_parser = subparsers.add_parser(name="list", help="Show existing integrations")
    list_parser.set_defaults(action="list")

    parser.set_defaults(func=integrations)


@inject
def pipelines(
    args,
    pipelines_api: PipelineApi = Provide[Container.pipeline_api],
    objectstore: ObjectStore = Provide[Container.object_store],
    streams_api: StreamsApi = Provide[Container.streams_api],
) -> None:
    match args.action:
        case "list":
            logging.info(pipelines_api.list())
        case "info":
            logging.info(str(pipelines_api.get(args.pipeline_id)))
        case "add":
            id = pipelines_api.create(name=args.name, stream_id=args.stream_id)
            logging.info(f"Created pipeline {args.name} with id {id}")
        case "list-runs":
            logging.info(pipelines_api._db.list_runs())
        case "logs":
            run = pipelines_api._db.get_run(args.run_id)
            if run:
                log = objectstore.get(run.log_hash).decode()
                print(log)
            else:
                logging.error(f"No pipeline run with id {args.run_id} found")
        case "add-step":
            step = list_steps()[args.step](**json.loads(args.step_params))
            new_pipeline = pipelines_api.add_step(args.pipeline_id, step)
            logging.info(f"Pipeline is now: {new_pipeline}")
        case "run":
            pipeline = pipelines_api.get(args.pipeline_id)
            pipeline(args.limit)


def pipelines_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(
        name="pipelines", help="Manage pipelines that create content."
    )
    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(name="add", help="Add a pipeline")
    add_parser.add_argument("name", help="What to name this pipeline")
    add_parser.add_argument(
        "stream_id", type=int, help="What stream this pipeline consumes"
    )
    add_parser.set_defaults(action="add")
    list_parser = subparsers.add_parser(name="list", help="List pipelines")
    list_parser.set_defaults(action="list")
    list_runs_parser = subparsers.add_parser(
        name="list-runs", help="Show a pipeline's runs"
    )
    list_runs_parser.set_defaults(action="list-runs")
    log_parser = subparsers.add_parser(
        name="logs", help="Show the log of a pipeline run"
    )
    log_parser.add_argument("run_id", type=int, help="The run id to show the logs for.")
    log_parser.set_defaults(action="logs")
    steps_parser = subparsers.add_parser(
        name="add-step", help="Add a step to a pipeline"
    )
    steps_parser.add_argument(
        "pipeline_id", type=int, help="The pipeline to add the step to."
    )
    steps_parser.add_argument(
        "step",
        type=str,
        help="The class name of the step to create for this step.",
        choices=list_steps().keys(),
    )
    steps_parser.add_argument(
        "step_params",
        type=str,
        help="A json object containing the parameters for this step.",
    )
    steps_parser.set_defaults(action="add-step")
    run_parser = subparsers.add_parser(name="run", help="Runs a pipeline")
    run_parser.add_argument("pipeline_id", help="Which pipeline to run.")
    run_parser.add_argument(
        "-l", "--limit", type=int, default=None, help="Only process this many media."
    )
    run_parser.set_defaults(action="run")
    info_parser = subparsers.add_parser(name="info", help="Displays a pipeline")
    info_parser.add_argument("pipeline_id", help="Which pipeline to display.")
    info_parser.set_defaults(action="info")
    parser.set_defaults(func=pipelines)


@inject
def frames(args, frames_api: FramesApi = Provide[Container.frames_api]) -> None:
    match args.action:
        case "list":
            logging.info(frames_api.list())
        case "remove":
            frames_api.remove(id=args.id)
            logging.info(f"Frame {args.id} has been deleted")
        case "add":
            options = json.loads(args.options) if args.options else {}
            frame = frames_api.add(name=args.name, **options)
            logging.info(f"Created new frame {frame.name} with id {frame.id}")


def frames_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(name="frames", help="Manage frames")
    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(name="add", help="Add a frame")
    add_parser.add_argument("name", help="What to name this frame")
    add_parser.add_argument(
        "-o", "--options", help="A json string of options for this frame"
    )
    add_parser.set_defaults(action="add")
    list_parser = subparsers.add_parser(name="list", help="List frames")
    list_parser.set_defaults(action="list")
    remove_parser = subparsers.add_parser(name="remove", help="Deletes a frame")
    remove_parser.set_defaults(action="remove")
    remove_parser.add_argument("id", help="The id of the frame to remove")
    parser.set_defaults(func=frames)


@inject
def uploads(args, uploads_api: UploadsApi = Provide[Container.uploads_api]) -> None:
    match args.action:
        case "list":
            logging.info(uploads_api.list())
        case "remove":
            uploads_api.remove(id=args.id)
            logging.info(f"Upload {args.id} has been deleted")
        case "add":
            with open(args.file, "rb") as fin:
                file_bytes = fin.read()
            result = uploads_api.add(file_bytes)
            logging.info("Resulting upload is:\n" + str(result.to_dict()))


def uploads_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(name="uploads", help="Manage uploads.")
    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(name="add", help="Injest some new media")
    add_parser.add_argument("file", help="The file to injest")
    add_parser.set_defaults(action="add")
    list_parser = subparsers.add_parser(name="list", help="List uploads")
    list_parser.set_defaults(action="list")
    remove_parser = subparsers.add_parser(name="remove", help="Deletes an upload")
    remove_parser.set_defaults(action="remove")
    remove_parser.add_argument("id", help="The id of the upload to remove")
    parser.set_defaults(func=uploads)


@inject
def prerenders(
    args, pre_render_api: PreRenderApi = Provide[Container.prerender_api]
) -> None:
    match args.action:
        case "list":
            logging.info(
                f"Pre renders available for {args.frame_id}:\n"
                + "\n".join(
                    [
                        pr.to_json()
                        for pr in pre_render_api.db.get_for_frame(
                            args.frame_id, sys.maxsize
                        )
                    ]
                )
            )
        case "create":
            result = pre_render_api.render_if_necessary(
                frame_id=args.frame_id,
                width=args.width,
                height=args.height,
                video_bitrate=args.bitrate,
            )
            logging.info("Resulting Pre Render is:\n" + str(result.to_json()))
        case "clean":
            pre_renders = pre_render_api.db.get_for_frame(args.frame_id, sys.maxsize)[
                1:
            ]
            logging.info(f"There are {len(pre_renders)} pre renders to clean.")
            for p in tqdm.tqdm(pre_renders, total=len(pre_renders)):
                pre_render_api.db.delete(p.id)
                pre_render_api.os.remove(p.video_hash)
            logging.info(f"Done cleaning frame {args.frame_id}.")


def pre_renders_parser(app_subparsers: argparse._SubParsersAction):
    parser = app_subparsers.add_parser(
        name="pre_renders", help="Manage frame pre-renders."
    )
    subparsers = parser.add_subparsers(metavar="action", required=True)
    add_parser = subparsers.add_parser(
        name="create", help="Creates a pre render for a frame"
    )
    add_parser.add_argument("frame_id", help="The frame to make the pre-render for.")
    add_parser.add_argument(
        "--width", type=int, default=1920, help="The width of the resulting video"
    )
    add_parser.add_argument(
        "--height", type=int, default=1080, help="The height of the resulting video"
    )
    add_parser.add_argument(
        "--bitrate", type=int, default=1200, help="The bitrate of the resulting video"
    )
    add_parser.set_defaults(action="create")
    list_parser = subparsers.add_parser(
        name="list", help="Lists pre renders for a frame."
    )
    list_parser.add_argument("frame_id", help="The frame to make the pre-render for.")
    list_parser.set_defaults(action="list")

    clean_parser = subparsers.add_parser(
        name="clean", help="Removes old pre-renders for a specific frame."
    )
    clean_parser.add_argument("frame_id", help="The frame to clean.")
    clean_parser.set_defaults(action="clean")

    parser.set_defaults(func=prerenders)


def main():
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    parser = argparse.ArgumentParser(
        prog="kinetic-cli", description="Command line interface for kinetic photos."
    )
    subparsers = parser.add_subparsers(metavar="command:", required=True)
    integrations_parser(subparsers)
    streams_parser(subparsers)
    pipelines_parser(subparsers)
    frames_parser(subparsers)
    uploads_parser(subparsers)
    pre_renders_parser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
