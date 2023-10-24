from pathlib import Path
import logging as log
import click

from infrapatch.core.composition import build_main_handler
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.models.versioned_terraform_resources import get_upgradable_resources
from git import Repo


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--default-registry-domain")
@click.option("--registry-secrets-string")
@click.option("--source-branch")
@click.option("--target-branch")
@click.option("--github-token")
@click.option("--report-only", is_flag=True)
@click.option("--working-directory")
@catch_exception(handle=Exception)
def main(debug: bool, default_registry_domain: str, registry_secrets_string: str, source_branch: str, target_branch: str, github_token: str, report_only: bool,
         working_directory: str):
    setup_logging(debug)

    main_handler = build_main_handler(default_registry_domain=default_registry_domain, credentials_dict=get_credentials_from_string(registry_secrets_string))
    resources = main_handler.get_all_terraform_resources(Path(project_root))

    if report_only:
        main_handler.print_resource_table(resources)
        return

    upgradable_resources = get_upgradable_resources(resources)
    if len(upgradable_resources) == 0:
        log.info("No upgradable resources found.")
        return

    repo = Repo(project_root)
    if repo.is_dirty():
        raise Exception("Repository is dirty. Please commit your changes before running infrapatch.")
    # check if the source branch exists
    if source_branch not in repo.branches:
        raise Exception(f"Source branch '{source_branch}' does not exist.")
    # check if the target branch exists
    if target_branch not in repo.branches:
        # create the target branch and switch to it
        repo.create_head(target_branch)
        repo.heads[target_branch].checkout()
    else:
        repo.heads[target_branch].checkout()
        # pull the latest changes
        repo.remotes.origin.pull()
    # check if the source branch is ahead of the target branch
    # if repo.heads[source_branch].commit != repo.heads[target_branch].commit:
    #     # rebase the target branch from the source branch
    #     repo.git.rebase(source_branch)


def get_credentials_from_string(credentials_string: str) -> dict:
    credentials = {}
    if credentials_string == "":
        return credentials
    # loop through each line in the string
    for line in credentials_string.splitlines():
        # split the line into name and token, separated by an equals sign, if multiple equals signs are present, only split on the first one
        name, token = line.split("=", 1)
        # add the name and token to the credentials dict
        credentials[name] = token


if __name__ == "__main__":
    main()
