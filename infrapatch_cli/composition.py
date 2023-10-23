import logging as log
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

import infrapatch_cli.constants as cs
from infrapatch_cli.hcl_handler import HclHandler
from infrapatch_cli.models import VersionedTerraformResource, TerraformModule, TerraformProvider, get_upgradable_resources
from infrapatch_cli.registry_handler import RegistryHandler


class MainHandler():
    def __init__(self, hcl_handler: HclHandler, registry_handler: RegistryHandler):
        self.hcl_handler = hcl_handler
        self.registry_handler = registry_handler

    def get_all_terraform_resources(self, project_root: Path) -> list[VersionedTerraformResource]:
        terraform_files = self.hcl_handler.get_all_terraform_files(project_root)
        if len(terraform_files) == 0:
            return []
        resources = []
        for terraform_file in terraform_files:
            resources.extend(self.hcl_handler.get_terraform_resources_from_file(terraform_file))
        for resource in resources:
            resource.set_newest_version(self.registry_handler.get_newest_version(resource))
        return resources

    def print_resource_table(self, resources: list[VersionedTerraformResource], only_upgradable: bool = False):
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

    def update_resources(self, resources: list[VersionedTerraformResource], confirm: bool):
        upgradable_resources = get_upgradable_resources(resources)
        if len(upgradable_resources) == 0:
            log.info("All resources are up to date, nothing to do.")
            return
        if not confirm:
            self.print_resource_table(resources, True)
            if not click.confirm("Do you want to apply the changes?"):
                print("Aborting...")
                return
        for resource in upgradable_resources:
            log.info(f"Updating '{resource.resource_name}' with name '{resource.name}' from version '{resource.current_version}' to '{resource.newest_version}'.")
            self.hcl_handler.bump_resource_version(resource)

    def _compose_resource_table(self, resources: list[VersionedTerraformResource], title: str):
        table = Table(show_header=True,
                      title=title,
                      width=cs.CLI_WIDTH
                      )
        table.add_column("Name")
        table.add_column("Current Version")
        table.add_column("Newest Version")
        table.add_column("Upgradeable")
        for resource in resources:
            table.add_row(
                resource.name,
                resource.current_version,
                resource.newest_version,
                str(not resource.installed_version_equal_or_newer_than_new_version())
            )
        console = Console()
        console.print(table)
