import logging as log
from typing import Union

import click
from github import Auth, Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from infrapatch.action.config import ActionConfigProvider
from infrapatch.core.log_helper import catch_exception, setup_logging
from infrapatch.core.provider_handler import ProviderHandler
from infrapatch.core.provider_handler_builder import ProviderHandlerBuilder
from infrapatch.core.utils.git import Git


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True)
@catch_exception(handle=Exception)
def main(debug: bool):
    setup_logging(debug)

    config = ActionConfigProvider()

    git = Git(config.repository_root)
    github = Github(auth=Auth.Token(config.github_token))
    github_repo = github.get_repo(config.repository_name)
    github_head_branch = github_repo.get_branch(config.head_branch)

    if len(config.enabled_providers) == 0:
        raise Exception("No providers enabled. Please enable at least one provider.")

    builder = ProviderHandlerBuilder(config.working_directory)
    builder.with_git_integration()
    if "terraform_modules" in config.enabled_providers or "terraform_providers" in config.enabled_providers:
        builder.add_terraform_registry_configuration(config.default_registry_domain, config.registry_secrets)
    if "terraform_modules" in config.enabled_providers:
        builder.with_terraform_module_provider()
    if "terraform_providers" in config.enabled_providers:
        builder.with_terraform_provider_provider()

    provider_handler = builder.build()

    git.fetch_origin()

    try:
        github_target_branch = github_repo.get_branch(config.target_branch)
    except GithubException:
        github_target_branch = None

    upgradable_resources_head_branch = None
    pr = None
    if github_target_branch is not None and config.report_only is False:
        pr = get_pr(github_repo, config.head_branch, config.target_branch)
        if pr is not None:
            upgradable_resources_head_branch = provider_handler.get_upgradable_resources()
        log.info(f"Branch {config.target_branch} already exists. Checking out...")
        git.checkout_branch(config.target_branch, f"origin/{config.target_branch}")

        log.info(f"Rebasing branch {config.target_branch} onto origin/{config.head_branch}")
        git.run_git_command(["rebase", "-Xtheirs", f"origin/{config.head_branch}"])
        git.push(["-f", "-u", "origin", config.target_branch])

    provider_handler.print_resource_table(only_upgradable=True, disable_cache=True)

    if config.report_only:
        log.info("Report only mode is enabled. No changes will be applied.")
        return

    if provider_handler.check_if_upgrades_available() is False:
        log.info("No resources with pending upgrade found.")
        return

    if github_target_branch is None:
        log.info(f"Branch {config.target_branch} does not exist. Creating and checking out...")
        github_repo.create_git_ref(ref=f"refs/heads/{config.target_branch}", sha=github_head_branch.commit.sha)
        git.checkout_branch(config.target_branch, f"origin/{config.head_branch}")

    provider_handler.upgrade_resources()
    if upgradable_resources_head_branch is not None:
        log.info("Updating status of resources from previous branch...")
        provider_handler.set_resources_patched_based_on_existing_resources(upgradable_resources_head_branch)
    provider_handler.print_statistics_table()
    provider_handler.dump_statistics()

    git.push(["-f", "-u", "origin", config.target_branch])

    body = get_pr_body(provider_handler)

    if pr is not None:
        pr.edit(body=body)
        return
    create_pr(github_repo, config.head_branch, config.target_branch, body)


def get_pr_body(provider_handler: ProviderHandler) -> str:
    body = ""
    markdown_tables = provider_handler.get_markdown_tables()
    for table in markdown_tables:
        body += table.dumps()
        body += "\n"

    body += provider_handler._get_statistics().get_markdown_table().dumps()
    body += "\n"
    return body


def get_pr(repo: Repository, head_branch, target_branch) -> Union[PullRequest, None]:
    pull = repo.get_pulls(state="open", sort="created", base=head_branch, head=target_branch)
    if pull.totalCount != 0:
        log.info(f"Pull request found from '{target_branch}' to '{head_branch}'")
        return pull[0]
    log.debug(f"No pull request found from '{target_branch}' to '{head_branch}'.")
    return None


def create_pr(repo: Repository, head_branch: str, target_branch: str, body: str) -> PullRequest:
    log.info(f"Creating new pull request from '{target_branch}' to '{head_branch}'.")
    return repo.create_pull(title="InfraPatch Module and Provider Update", body=body, base=head_branch, head=target_branch)


if __name__ == "__main__":
    main()
