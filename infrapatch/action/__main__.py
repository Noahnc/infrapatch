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
@click.option("--source-branch-name")
@click.option("--target-branch-name")
@click.option("--github-token")
@click.option("--report-only", is_flag=True)
@click.option("--working-directory")
@click.option("--do-not-push", is_flag=True)
@catch_exception(handle=Exception)
def main(debug: bool, default_registry_domain: str, registry_secrets_string: str, source_branch_name: str, target_branch_name: str, github_token: str, report_only: bool,
         working_directory: str,
         do_not_push: bool):

    setup_logging(debug)
    log.debug(f"Running infrapatch with the following parameters: "
              f"default_registry_domain={default_registry_domain}, "
              f"registry_secrets_string={registry_secrets_string}, "
              f"source_branch={source_branch_name}, "
              f"target_branch={target_branch_name}, "
              f"github_token={github_token}, "
              f"report_only={report_only}, "
              f"working_directory={working_directory}"
              )
    credentials = {}
    if registry_secrets_string is not None:
        credentials = get_credentials_from_string(registry_secrets_string)
    main_handler = build_main_handler(default_registry_domain=default_registry_domain, credentials_dict=credentials)
    # resources = main_handler.get_all_terraform_resources(Path(working_directory))
    #
    # if report_only:
    #     main_handler.print_resource_table(resources)
    #     log.info("Report only mode is enabled. No changes will be applied.")
    #     return
    #
    # upgradable_resources = get_upgradable_resources(resources)
    # if len(upgradable_resources) == 0:
    #     log.info("No upgradable resources found.")
    #     return

    repo = Repository(working_directory)
    # if repo.is_dirty():
    #     raise Exception("Repository is dirty. Please commit your changes before running infrapatch.")
    # check if the source branch exists

    # Replace these with your own values
    remote_name = "origin"
    source_branch_ref = f"{remote_name}/{source_branch_name}"
    target_branch_ref = f"{remote_name}/{target_branch_name}"
    source_branch = repo.lookup_branch(source_branch_ref, pygit2.GIT_BRANCH_REMOTE)
    if source_branch is None:
        raise Exception(f"Source branch '{source_branch_name}' does not exist in remote '{remote_name}'.")

    # Fetch the source branch
    remote = repo.remotes[remote_name]
    remote.fetch()

    # Check if the target branch exists
    target_branch_ref = f"refs/remotes/{remote_name}/{target_branch_name}"
    target_branch = repo.lookup_branch(target_branch_ref, pygit2.GIT_BRANCH_REMOTE)

    # Fetch the target branch if it exists
    if target_branch is not None:
        remote.fetch(target_branch_name)

    target_branch = repo.lookup_branch(target_branch_ref)

    source_branch = [branch for branch in repo.remotes if branch.name == source_branch_ref]
    target_branch = [branch for branch in repo.remotes if branch.name == target_branch_ref]

    if len(source_branch) == 0:
        raise Exception(f"Source branch '{source_branch_ref}' does not exist.")
    source_branch = source_branch[0]

    source_branch.fetch()

    if len(target_branch) == 0:
        target_branch = repo.remotes.create(target_branch_name)
    else:
        target_branch = target_branch[0]
        target_branch.fetch()

    target_branch.checkout()

def push(repo, branch, remote_name='origin'):
    ref = f"refs/heads/{branch}:refs/heads/{branch}"
    for remote in repo.remotes:
        if remote.name == remote_name:
            remote.push(ref)


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
