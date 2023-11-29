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
    builder.with_git_integration(config.repository_root)
    if "terraform_modules" in config.enabled_providers or "terraform_providers" in config.enabled_providers:
        builder.add_terraform_registry_configuration(config.default_registry_domain, config.terraform_registry_secrets)
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
        pr = get_pr(github_repo, head=config.target_branch, base=config.head_branch)
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
        if pr is not None and upgradable_resources_head_branch is not None:
            log.info("Updating PR Body...")
            provider_handler.set_resources_patched_based_on_existing_resources(upgradable_resources_head_branch)
            update_pr_body(pr, provider_handler)
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

    if pr is not None:
        update_pr_body(pr, provider_handler)
        return
    create_pr(github_repo, config.head_branch, config.target_branch, provider_handler)


def update_pr_body(pr, provider_handler):
    if pr is not None:
        log.info("Updating existing pull request with new body.")
        body = get_pr_body(provider_handler)
        log.debug(f"Pull request body:\n{body}")
        pr.edit(body=body)
        return


def get_pr_body(provider_handler: ProviderHandler) -> str:
    body = ""
    markdown_tables = provider_handler.get_markdown_table_for_changed_resources()
    for table in markdown_tables:
        body += table.dumps()
        body += "\n"

    body += provider_handler._get_statistics().get_markdown_table().dumps()
    body += "\n"
    return body


def get_pr(repo: Repository, base: str, head: str) -> Union[PullRequest, None]:
    base_ref = base
    head_ref = head
    if base_ref.startswith("origin/"):
        base_ref = base_ref[len("origin/") :]
    if head_ref.startswith("origin/"):
        head_ref = head_ref[len("origin/") :]
    pulls = repo.get_pulls(state="open", sort="created", direction="desc")

    if pulls.totalCount == 0:
        log.debug("No pull request found")
        return None

    pr = [pr for pr in pulls if pr.base.ref == base_ref and pr.head.ref == head_ref]
    if len(pr) == 0:
        log.debug(f"No pull request found from '{head}' to '{base}'.")
        return None
    elif len(pr) == 1:
        log.debug(f"Pull request found from '{head}' to '{base}'.")
        return pr[0]
    if len(pr) > 1:
        raise Exception(f"Multiple pull requests found from '{head}' to '{base}'.")


def create_pr(repo: Repository, head_branch: str, target_branch: str, provider_handler: ProviderHandler) -> PullRequest:
    body = get_pr_body(provider_handler)
    log.info(f"Creating new pull request from '{target_branch}' to '{head_branch}'.")
    log.debug(f"Pull request body:\n{body}")
    return repo.create_pull(title="InfraPatch Module and Provider Update", body=body, base=head_branch, head=target_branch)


if __name__ == "__main__":
    main()
