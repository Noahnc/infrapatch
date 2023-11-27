import json
import logging as log
from pathlib import Path
from typing import Sequence, Union

import click
from git import Repo
from rich import progress
from rich.console import Console
from rich.table import Table

import infrapatch.core.constants as cs
from infrapatch.core.credentials_helper import get_registry_credentials
from infrapatch.core.models.versioned_terraform_resources import (
    VersionedTerraformResource,
    TerraformModule,
    TerraformProvider,
    get_upgradable_resources,
    ResourceStatus,
    from_terraform_resources_to_dict_list,
)
from infrapatch.core.utils.hcl_edit_cli import HclEditCliException, HclEditCli
from infrapatch.core.utils.hcl_handler import HclHandler
from infrapatch.core.utils.registry_handler import RegistryHandler


def build_main_handler(default_registry_domain: str, credentials_file: Union[Path, None] = None, credentials_dict: Union[dict, None] = None):
    hcl_edit_cli = HclEditCli()
    hcl_handler = HclHandler(hcl_edit_cli)
    if credentials_dict is None:
        credentials_dict = get_registry_credentials(hcl_handler, credentials_file)
    registry_handler = RegistryHandler(default_registry_domain, credentials_dict)
    return MainHandler(hcl_handler, registry_handler, Console(width=cs.CLI_WIDTH))


class MainHandler:
    def __init__(self, hcl_handler: HclHandler, registry_handler: RegistryHandler, console: Console):
        self.hcl_handler = hcl_handler
        self.registry_handler = registry_handler
        self._console = console

    def get_all_terraform_resources(self, project_root: Path) -> Sequence[VersionedTerraformResource]:
        log.info(f"Searching for .tf files in {project_root.absolute().as_posix()} ...")
        terraform_files = self.hcl_handler.get_all_terraform_files(project_root)
        if len(terraform_files) == 0:
            return []
        resources = []
        for terraform_file in progress.track(terraform_files, description="Parsing .tf files..."):
            resources.extend(self.hcl_handler.get_terraform_resources_from_file(terraform_file))
        for resource in progress.track(resources, description="Getting newest resource versions..."):
            resource.newest_version = self.registry_handler.get_newest_version(resource)
        return resources

    def print_resource_table(self, resources: Sequence[VersionedTerraformResource], only_upgradable: bool = False):
        if len(resources) == 0:
            print("No resources found.")
            return
        provider_resources = [resource for resource in resources if isinstance(resource, TerraformProvider)]
        module_resources = [resource for resource in resources if isinstance(resource, TerraformModule)]

        if only_upgradable:
            upgradeable_provider_resources = [resource for resource in provider_resources if not resource.installed_version_equal_or_newer_than_new_version()]
            upgradeable_module_resources = [resource for resource in module_resources if not resource.installed_version_equal_or_newer_than_new_version()]
            if len(upgradeable_module_resources) == 0 and len(upgradeable_provider_resources) == 0:
                print("All resources are up to date.")
                return
            if len(upgradeable_module_resources) > 0:
                self._compose_resource_table(upgradeable_module_resources, "Upgradeable Modules")
            else:
                print("No upgradeable modules found.")
            if len(upgradeable_provider_resources) > 0:
                self._compose_resource_table(upgradeable_provider_resources, "Upgradeable Providers")
            else:
                print("No upgradeable providers found.")
            return
        if len(module_resources) > 0:
            sorted_module_resources = sorted(module_resources, key=lambda resource: resource.installed_version_equal_or_newer_than_new_version())
            self._compose_resource_table(sorted_module_resources, "Modules")
        else:
            print("No modules found.")
        if len(provider_resources) > 0:
            sorted_provider_resources = sorted(provider_resources, key=lambda resource: resource.installed_version_equal_or_newer_than_new_version())
            self._compose_resource_table(sorted_provider_resources, "Providers")
        else:
            print("No providers found.")

    # noinspection PyUnboundLocalVariable
    def update_resources(
        self, resources: Sequence[VersionedTerraformResource], confirm: bool, working_dir: Path, repo_root: Path, commit_changes: bool = False
    ) -> Sequence[VersionedTerraformResource]:
        upgradable_resources = get_upgradable_resources(resources)
        if len(upgradable_resources) == 0:
            log.info("All resources are up to date, nothing to do.")
            return []
        repo: Union[Repo, None] = None
        if commit_changes:
            repo = Repo(path=working_dir.absolute().as_posix())
            if repo.bare:
                raise Exception("Working directory is not a git repository.")
            log.info(f"Committing changes to git branch '{repo.active_branch.name}'.")
        self.print_resource_table(resources, True)
        if not confirm:
            if not click.confirm("Do you want to apply the changes?"):
                print("Aborting...")
                return []
        for resource in progress.track(upgradable_resources, description="Updating resource versions..."):
            try:
                self.hcl_handler.bump_resource_version(resource)
            except HclEditCliException as e:
                log.error(f"Could not update resource '{resource.name}': {e}")
                resource.set_patch_error()
                continue
            if commit_changes:
                if repo is None:
                    raise Exception("repo is None.")
                repo.index.add([resource.source_file.absolute().as_posix()])
                repo.index.commit(f"Bump {resource.resource_name} '{resource.name}' from version '{resource.current_version}' to '{resource.newest_version}'.")
            resource.set_patched()
        return upgradable_resources

    def _compose_resource_table(self, resources: Sequence[VersionedTerraformResource], title: str):
        table = Table(show_header=True, title=title, expand=True)
        table.add_column("Name", overflow="fold")
        table.add_column("Source", overflow="fold")
        table.add_column("Current")
        table.add_column("Newest")
        table.add_column("Upgradeable")
        for resource in resources:
            table.add_row(resource.name, resource.source, resource.current_version, resource.newest_version, str(not resource.installed_version_equal_or_newer_than_new_version()))
        self._console.print(table)

    def dump_statistics(self, resources, save_as_json_file: bool = False):
        providers = [resource for resource in resources if isinstance(resource, TerraformProvider)]
        modules = [resource for resource in resources if isinstance(resource, TerraformModule)]
        statistics = {}
        statistics["errors"] = len([resource for resource in resources if resource.status == ResourceStatus.PATCH_ERROR])
        statistics["resources_patched"] = len([resource for resource in resources if resource.status == ResourceStatus.PATCHED])
        statistics["resources_pending_update"] = len([resource for resource in resources if resource.check_if_up_to_date() is False])
        statistics["total_resources"] = len(resources)
        statistics["modules_count"] = len(modules)
        statistics["providers_count"] = len(providers)
        statistics["modules"] = from_terraform_resources_to_dict_list(modules)
        statistics["providers"] = from_terraform_resources_to_dict_list(providers)
        if save_as_json_file:
            file = Path(f"{cs.APP_NAME}_Statistics.json")
            if file.exists():
                file.unlink()
            with open(file, "w") as f:
                f.write(json.dumps(statistics))
        table = Table(show_header=True, title="Statistics", expand=True)
        table.add_column("Total Resources")
        table.add_column("Resources Pending Update")
        table.add_column("Resources Patched")
        table.add_column("Errors")
        table.add_column("Modules")
        table.add_column("Providers")
        table.add_row(
            str(statistics["total_resources"]),
            str(statistics["resources_pending_update"]),
            str(statistics["resources_patched"]),
            str(statistics["errors"]),
            str(statistics["modules_count"]),
            str(statistics["providers_count"]),
        )
        self._console.print(table)
