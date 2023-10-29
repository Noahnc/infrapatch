import json
import logging as log
from functools import partial, wraps
from pathlib import Path

import click
from rich.console import Console

import infrapatch.core.constants as cs
from infrapatch.cli.__init__ import __version__
from infrapatch.core.composition import MainHandler, build_main_handler
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.utils.hcl_edit_cli import HclEditCli
from infrapatch.core.utils.hcl_handler import HclHandler
from infrapatch.core.utils.registry_handler import RegistryHandler

main_handler: MainHandler = None


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--version", is_flag=True, help="Prints the version of the tool.")
@click.option("--credentials-file-path", default=None, help="Path to a file containing credentials for private registries.")
@click.option("--default_registry_domain", default="registry.terraform.io", help="Default registry domain for resources without a specified domain.")
@catch_exception(handle=Exception)
def main(debug: bool, version: bool, credentials_file_path: str, default_registry_domain: str):
    if version:
        print(f"You are running infrapatch version: {__version__}")
        exit(0)
    setup_logging(debug)
    global main_handler
    main_handler = build_main_handler(default_registry_domain, credentials_file_path)


# noinspection PyUnresolvedReferences
@main.command()
@click.option("project_root", "--project-root", default=None, help="Root directory of the project. If not specified, the current working directory is used.")
@click.option("--only-upgradable", is_flag=True, help="Only show providers and modules that can be upgraded.")
@click.option("--dump-json-statistics", is_flag=True, help="Creates a json file containing statistics about the found resources and there update status as json file in the cwd.")
@catch_exception(handle=Exception)
def report(project_root: str, only_upgradable: bool, dump_json_statistics: bool):
    """Finds all modules and providers in the project_root and prints the newest version."""
    if project_root is None: project_root = Path.cwd()
    global main_handler
    resources = main_handler.get_all_terraform_resources(Path(project_root))
    main_handler.print_resource_table(resources, only_upgradable)
    main_handler.dump_statistics(resources, dump_json_statistics)


@main.command()
@click.option("project_root", "--project-root", default=None, help="Root directory of the project. If not specified, the current working directory is used.")
@click.option("--confirm", is_flag=True, help="Apply changes without confirmation.")
@click.option("--dump-json-statistics", is_flag=True, help="Creates a json file containing statistics about the updated resources in the cwd.")
@catch_exception(handle=Exception)
def update(project_root: str, confirm: bool, dump_json_statistics: bool):
    """Finds all modules and providers in the project_root and updates them to the newest version."""
    if project_root is None: project_root = Path.cwd()
    global main_handler
    resources = main_handler.get_all_terraform_resources(Path(project_root))
    main_handler.update_resources(resources, confirm, Path(project_root))
    main_handler.dump_statistics(resources, dump_json_statistics)
