import json
import subprocess
from pathlib import Path
import logging as log
import click
from github import Auth, Github
from github.PullRequest import PullRequest

from infrapatch.core.composition import build_main_handler
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.models.versioned_terraform_resources import get_upgradable_resources
from pygit2 import Repository, Remote


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True)
@click.option("--default-registry-domain")
@click.option("--registry-secrets-string", default=None)
@click.option("--github-token")
@click.option("--target-branch")
@click.option("--head-branch")
@click.option("--repository-name")
@click.option("--report-only", is_flag=True)
@click.option("--working-directory")
@catch_exception(handle=Exception)
def main(debug: bool, default_registry_domain: str, registry_secrets_string: str, github_token: str, target_branch: str, head_branch: str, repository_name: str, report_only: bool,
         working_directory: str):
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

    main_handler.print_resource_table(upgradable_resources)
    main_handler.update_resources(upgradable_resources, True, working_directory, True)
    main_handler.dump_statistics(upgradable_resources, save_as_json_file=True)

    push_changes(target_branch, working_directory)

    create_pr(github_token, head_branch, repository_name, target_branch)


def push_changes(target_branch, working_directory):
    command = ["git", "push", "-f", "-u", "origin", target_branch]
    log.debug(f"Executing command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, cwd=working_directory.absolute().as_posix())
    except Exception as e:
        raise Exception(f"Error pushing to remote: {e}")
    if result.returncode != 0:
        log.error(f"Stdout: {result.stdout}")
        raise Exception(f"Error pushing to remote: {result.stderr}")


def create_pr(github_token, head_branch, repository_name, target_branch) -> PullRequest:
    token = Auth.Token(github_token)
    github = Github(auth=token)
    repo = github.get_repo(repository_name)
    pull = repo.get_pulls(state='open', sort='created', base=head_branch, head=target_branch)
    if pull.totalCount != 0:
        log.info(f"Pull request found from '{target_branch}' to '{head_branch}'")
        return pull[0]
    log.info(f"No pull request found from '{target_branch}' to '{head_branch}'. Creating a new one.")
    return repo.create_pull(title=f"InfraPatch Module and Provider Update", body=f"InfraPatch Module and Provider Update", base=head_branch, head=target_branch)


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
