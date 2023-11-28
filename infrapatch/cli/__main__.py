from pathlib import Path
from typing import Union

import click
from infrapatch.core.credentials_helper import get_registry_credentials
from infrapatch.core.provider_handler import ProviderHandler
from infrapatch.core.provider_handler_builder import ProviderHandlerBuilder

from infrapatch.cli.__init__ import __version__
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli
from infrapatch.core.utils.terraform.hcl_handler import HclHandler

provider_handler: Union[ProviderHandler, None] = None


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--version", is_flag=True, help="Prints the version of the tool.")
@click.option("--working-directory-path", default=None, help="Working directory to run. Defaults to the current working directory")
@click.option("--credentials-file-path", default=None, help="Path to a file containing credentials for private registries.")
@click.option("--default-registry-domain", default="registry.terraform.io", help="Default registry domain for resources without a specified domain.")
@catch_exception(handle=Exception)
def main(debug: bool, version: bool, working_directory_path: str, credentials_file_path: str, default_registry_domain: str):
    if version:
        print(f"You are running infrapatch version: {__version__}")
        exit(0)
    setup_logging(debug)

    global provider_handler
    credentials_file = None
    working_directory = Path.cwd()

    if working_directory_path is not None:
        working_directory = Path(working_directory_path)
        if not working_directory.exists() or not working_directory.is_dir():
            raise Exception(f"Project root '{working_directory.absolute().as_posix()}' does not exist.")

    if credentials_file_path is not None:
        credentials_file = Path(credentials_file_path)
        if not credentials_file.exists() or not credentials_file.is_file():
            raise Exception(f"Credentials file '{credentials_file}' does not exist.")
    credentials = get_registry_credentials(HclHandler(HclEditCli()), credentials_file)
    provider_builder = ProviderHandlerBuilder(working_directory)
    provider_builder.add_terraform_registry_configuration(default_registry_domain, credentials)
    provider_builder.with_terraform_module_provider()
    provider_builder.with_terraform_provider_provider()
    provider_handler = provider_builder.build()


# noinspection PyUnresolvedReferences
@main.command()
@click.option("--only-upgradable", is_flag=True, help="Only show providers and modules that can be upgraded.")
@click.option("--dump-json-statistics", is_flag=True, help="Creates a json file containing statistics about the found resources and there update status as json file in the cwd.")
@catch_exception(handle=Exception)
def report(only_upgradable: bool, dump_json_statistics: bool):
    """Finds all modules and providers in the project_root and prints the newest version."""
    if provider_handler is None:
        raise Exception("provider_handler not initialized.")
    provider_handler.print_resource_table(only_upgradable)
    provider_handler.print_statistics_table()
    if dump_json_statistics:
        provider_handler.dump_statistics()


@main.command()
@click.option("--confirm", is_flag=True, help="Apply changes without confirmation.")
@click.option("--dump-json-statistics", is_flag=True, help="Creates a json file containing statistics about the updated resources in the cwd.")
@catch_exception(handle=Exception)
def update(confirm: bool, dump_json_statistics: bool):
    """Finds all modules and providers in the project_root and updates them to the newest version."""
    global provider_handler
    if provider_handler is None:
        raise Exception("main_handler not initialized.")

    provider_handler.print_resource_table(only_upgradable=True)
    if not confirm:
        if not click.confirm("Do you want to apply the changes?"):
            print("Aborting...")
            return

    provider_handler.upgrade_resources()
    provider_handler.print_statistics_table()
    if dump_json_statistics:
        provider_handler.dump_statistics()


if __name__ == "__main__":
    main()
