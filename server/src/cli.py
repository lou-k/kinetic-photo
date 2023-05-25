import argparse
import itertools
import json
import logging

from dependency_injector.wiring import Provide, inject

from containers import Container
from integrations import IntegrationsApi, IntegrationType
from streams import StreamsApi, StreamType


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
                in set([StreamType.Google_Photos_Album, StreamType.Google_Photos_Search])
                and not args.integration
            ):
                raise Exception(
                    f"An intgration id must be set when creating streams of type {typ.name}"
                )

            stream_id = streams_api.add(
                name=args.name,
                typ=typ,
                integration_id=args.integration,
                params=params,
                filter=args.filter,
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
    add_parser.add_argument(
        "-f", "--filter", help="A json-path filter to apply over the stream media", type=str
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


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    parser = argparse.ArgumentParser(
        prog="kinetic-cli", description="Command line interface for kinetic photos."
    )
    subparsers = parser.add_subparsers(metavar="command:", required=True)
    integrations_parser(subparsers)
    streams_parser(subparsers)

    args = parser.parse_args()
    args.func(args)
