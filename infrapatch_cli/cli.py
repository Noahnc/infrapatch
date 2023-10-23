import json
import logging as log
from functools import partial, wraps
from pathlib import Path

import click
from rich.console import Console

import infrapatch_cli.constants as cs
from infrapatch_cli.__init__ import __version__
from infrapatch_cli.composition import MainHandler
from infrapatch_cli.hcl_edit_cli import HclEditCli
from infrapatch_cli.hcl_handler import HclHandler
from infrapatch_cli.registry_handler import RegistryHandler

composition = None
debug_exception = False


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            if debug_exception:
                Console().print_exception()
            else:
                log.error("An error occurred: " + str(e))

    return wrapper


def setup_logging(debug: bool = False):
    log_level = log.INFO
    if debug:
        log_level = log.DEBUG
    log.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')


def get_registry_credentials(hcl_handler: HclHandler, credentials_file: str = None) -> dict[str, str]:
    credentials =  hcl_handler.get_credentials_form_user_rc_file()
    if credentials_file is None:
        credentials_file = Path.cwd().joinpath(cs.DEFAULT_CREDENTIALS_FILE_NAME)
    else:
        credentials_file = Path(credentials_file)
    if not credentials_file.exists() or not credentials_file.is_file():
        log.debug(f"No credentials file found at '{credentials_file}'.")
        return credentials
    try:
        with open(credentials_file.absolute(), "r") as file:
            credentials_file_dict = json.load(file)
            for name, token in credentials_file_dict.items():
                log.debug(f"Found the following credentials in credentials file: {name}={token[0:5]}...")
                if name in credentials:
                    log.debug(f"Credentials for registry '{name}' already found in terraformrc file and credentials file, using value from credentials file.")
                credentials[name] = token
        return credentials
    except Exception as e:
        raise Exception(f"Could not read credentials file: {e}")



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
    hcl_edit_cli = HclEditCli()
    hcl_handler = HclHandler(hcl_edit_cli)
    credentials = get_registry_credentials(hcl_handler, credentials_file_path)
    registry_handler = RegistryHandler(default_registry_domain, credentials)
    global composition
    composition = MainHandler(hcl_handler, registry_handler)
    global debug_exception
    debug_exception = debug


@main.command()
@click.option("project_root", "--project-root", default=None, help="Root directory of the project. If not specified, the current working directory is used.")
@click.option("--only-upgradable", is_flag=True, help="Only show providers and modules that can be upgraded.")
@catch_exception(handle=Exception)
def list(project_root: str, only_upgradable: bool):
    """Finds all modules and providers in the project_root and prints there newest version."""
    if project_root is None: project_root = Path.cwd()
    global composition
    resources = composition.get_all_terraform_resources(Path(project_root))
    composition.print_resource_table(resources, only_upgradable)

@main.command()
@click.option("project_root", "--project-root", default=None, help="Root directory of the project. If not specified, the current working directory is used.")
@click.option("--confirm", is_flag=True, help="Apply changes without confirmation.")
@catch_exception(handle=Exception)
def update(project_root: str, confirm: bool):
    if project_root is None: project_root = Path.cwd()
    global composition
    resources = composition.get_all_terraform_resources(Path(project_root))
    composition.update_resources(resources, confirm)
