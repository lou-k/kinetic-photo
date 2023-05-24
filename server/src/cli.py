import argparse
import json
import logging

from dependency_injector.wiring import Provide, inject

from containers import Container
from integrations import IntegrationsApi, IntegrationType


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
            if args.params:
                params = params
            elif args.params_file:
                with open(args.params_file) as fin:
                    params = json.load(fin)
            else:
                raise RuntimeError(
                    f'Either "params" or "params-file" arguments must be set.'
                )

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
        "-p",
        "--params",
        help="The json parameters of the credientials to store",
        type=str,
    )
    add_parser.add_argument(
        "-f", "--params-file", help="The filename to load the parmaters from", type=str
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

    logging.info("LOG TEST")

    parser = argparse.ArgumentParser(
        prog="kinetic-cli", description="Command line interface for kinetic photos."
    )
    subparsers = parser.add_subparsers(metavar="command:", required=True)
    integrations_parser(subparsers)

    args = parser.parse_args()
    args.func(args)
