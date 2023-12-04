import logging as log
from abc import abstractmethod
from pathlib import Path
from typing import Any, Sequence, Union

from github import Github
from pytablewriter import MarkdownTableWriter
from rich import progress
from rich.table import Table

from infrapatch.core.models.versioned_resource import VersionedResource, VersionedResourceReleaseNotes
from infrapatch.core.models.versioned_terraform_resources import VersionedTerraformResource
from infrapatch.core.providers.base_provider_interface import BaseProviderInterface
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCliInterface
from infrapatch.core.utils.terraform.hcl_handler import HclHandlerInterface
from infrapatch.core.utils.terraform.registry_handler import RegistryHandlerInterface


class TerraformProvider(BaseProviderInterface):
    def __init__(
        self, hcledit: HclEditCliInterface, registry_handler: RegistryHandlerInterface, hcl_handler: HclHandlerInterface, project_root: Path, github: Union[Github, None]
    ) -> None:
        self.hcledit = hcledit
        self.registry_handler = registry_handler
        self.hcl_handler = hcl_handler
        self.project_root = project_root
        self._github = github

    @abstractmethod
    def get_provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_provider_display_name(self) -> str:
        raise NotImplementedError

    def get_resources(self) -> Sequence[VersionedResource]:
        log.info(f"Searching for .tf files in {self.project_root.absolute().as_posix()} ...")
        terraform_files = self.hcl_handler.get_all_terraform_files(self.project_root)
        if len(terraform_files) == 0:
            return []

        resources = []
        for terraform_file in progress.track(terraform_files, description=f"Parsing .tf files for {self.get_provider_display_name()}..."):
            if self.get_provider_name() == "terraform_modules":
                resources.extend(self.hcl_handler.get_terraform_resources_from_file(terraform_file, get_modules=True, get_providers=False))

            elif self.get_provider_name() == "terraform_providers":
                resources.extend(self.hcl_handler.get_terraform_resources_from_file(terraform_file, get_modules=False, get_providers=True))

            else:
                raise Exception(f"Provider name '{self.get_provider_name()}' is not implemented.")

        for resource in progress.track(resources, description=f"Getting newest resource versions for Provider {self.get_provider_display_name()}..."):
            resource.newest_version = self.registry_handler.get_newest_version(resource)
            source = self.registry_handler.get_source(resource)
            if source is not None and "github.com" in source:
                resource.set_github_repo(source)
        return resources

    def patch_resource(self, resource: VersionedTerraformResource) -> VersionedTerraformResource:
        if resource.check_if_up_to_date() is True:
            log.debug(f"Resource '{resource.name}' is already up to date.")
            return resource
        self.hcl_handler.bump_resource_version(resource)
        return resource

    def get_rich_table(self, resources: Sequence[VersionedTerraformResource]) -> Table:
        table = Table(show_header=True, title=self.get_provider_display_name(), expand=True)
        table.add_column("Name", overflow="fold")
        table.add_column("Source", overflow="fold")
        table.add_column("Current")
        table.add_column("Newest")
        table.add_column("Status")
        for resource in resources:
            table.add_row(resource.name, resource.source, resource.current_version, resource.newest_version, resource.status)
        return table

    def get_markdown_table(self, resources: Sequence[VersionedTerraformResource]) -> MarkdownTableWriter:
        dict_list = []
        for resource in resources:
            dict_element = {
                "Name": resource.name,
                "Source": resource.source,
                "Current": resource.current_version,
                "Newest": resource.newest_version,
                "Status": resource.status,
            }
            dict_list.append(dict_element)
        return MarkdownTableWriter(
            table_name=self.get_provider_display_name(),
            headers=list(dict_list[0].keys()),
            value_matrix=[list(dict_element.values()) for dict_element in dict_list],
        )

    def get_resources_as_dict_list(self, resources: Sequence[VersionedTerraformResource]) -> list[dict[str, Any]]:
        return [resource.to_dict() for resource in resources]

    def get_resource_release_notes(self, resource: VersionedTerraformResource) -> Union[VersionedResourceReleaseNotes, None]:
        if resource.newest_version is None:
            raise Exception(f"Newest version of resource '{resource.name}' is not set.")
        if self._github is None:
            raise Exception("Github integration is not enabled.")
        if resource.github_repo is None:
            log.debug(f"Resource '{resource.name}' has no github repo set, skipping release notes.")
            return None
        try:
            repo = self._github.get_repo(resource.github_repo)
            release_notes = repo.get_release(f"v{resource.newest_version}").body
        except Exception as e:
            log.warning(f"Could not get release notes from repo '{resource.github_repo}' for version '{resource.newest_version}': {e}")
            return None
        return VersionedResourceReleaseNotes(resources=[resource], body=release_notes, name=resource.source, version=resource.newest_version)

    def get_grouped_by_identifier(self, resources: Sequence[VersionedTerraformResource]) -> dict[str, Sequence[VersionedTerraformResource]]:
        identifiers: dict[str, Sequence[VersionedTerraformResource]] = {}
        for resource in resources:
            if resource.source not in identifiers:
                identifiers[resource.source] = [resource]
                continue
            list(identifiers[resource.source]).append(resource)
        return identifiers
