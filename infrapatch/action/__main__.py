from pathlib import Path
import logging as log
import click
import pygit2

from infrapatch.core.composition import build_main_handler
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.models.versioned_terraform_resources import get_upgradable_resources
from pygit2 import Repository, Remote


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True)
@click.option("--default-registry-domain")
@click.option("--registry-secrets-string", default=None)
@click.option("--github-token")
@click.option("--report-only", is_flag=True)
@click.option("--working-directory")
@click.option("--do-not-push", is_flag=True)
@catch_exception(handle=Exception)
def main(debug: bool, default_registry_domain: str, registry_secrets_string: str, github_token: str, report_only: bool,
         working_directory: str,
         do_not_push: bool):
    setup_logging(debug)
    log.debug(f"Running infrapatch with the following parameters: "
              f"default_registry_domain={default_registry_domain}, "
              f"registry_secrets_string={registry_secrets_string}, "
              f"github_token={github_token}, "
              f"report_only={report_only}, "
              f"working_directory={working_directory}"
              )
    credentials = {}
    working_directory = Path(working_directory)
    if registry_secrets_string is not None:
        credentials = get_credentials_from_string(registry_secrets_string)
    main_handler = build_main_handler(default_registry_domain=default_registry_domain, credentials_dict=credentials)
    resources = main_handler.get_all_terraform_resources(working_directory)

    if report_only:
        main_handler.print_resource_table(resources)
        log.info("Report only mode is enabled. No changes will be applied.")
        return

    upgradable_resources = get_upgradable_resources(resources)
    if len(upgradable_resources) == 0:
        log.info("No upgradable resources found.")
        return

    main_handler.update_resources(upgradable_resources, confirm=False, working_dir=working_directory, commit_changes=True)


def get_credentials_from_string(credentials_string: str) -> dict:
    credentials = {}
    if credentials_string == "":
        return credentials
    for line in credentials_string.splitlines():
        try:
            name, token = line.split("=", 1)
        except ValueError as e:
            log.debug(f"Secrets line '{line}' could not be split into name and token.")
            raise Exception(f"Error processing secrets: '{e}'")
        # add the name and token to the credentials dict
        credentials[name] = token
    return credentials


if __name__ == "__main__":
    main()
