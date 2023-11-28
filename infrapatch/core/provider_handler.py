import json
import logging as log
from pathlib import Path
from typing import Sequence, Union
from git import Repo
from pytablewriter import MarkdownTableWriter
from rich.console import Console

from infrapatch.core.models.statistics import ProviderStatistics, Statistics
from infrapatch.core.models.versioned_resource import ResourceStatus, VersionedResource
from infrapatch.core.providers.base_provider_interface import BaseProviderInterface


class ProviderHandler:
    def __init__(self, providers: Sequence[BaseProviderInterface], console: Console, statistics_file: Path, repo: Union[Repo, None] = None) -> None:
        self.providers: dict[str, BaseProviderInterface] = {}
        for provider in providers:
            self.providers[provider.get_provider_name()] = provider

        self._resource_cache: dict[str, Sequence[VersionedResource]] = {}
        self.console = console
        self.statistics_file = statistics_file
        self.repo = repo

    def get_resources(self, disable_cache: bool = False) -> dict[str, Sequence[VersionedResource]]:
        for provider_name, provider in self.providers.items():
            if not disable_cache and provider_name not in self._resource_cache:
                self._resource_cache[provider.get_provider_name()] = provider.get_resources()
        return self._resource_cache

    def get_upgradable_resources(self, disable_cache: bool = False) -> dict[str, Sequence[VersionedResource]]:
        upgradable_resources: dict[str, Sequence[VersionedResource]] = {}
        resources = self.get_resources(disable_cache)
        for provider_name, provider in self.providers.items():
            upgradable_resources[provider.get_provider_name()] = [resource for resource in resources[provider.get_provider_name()] if not resource.check_if_up_to_date()]
        return upgradable_resources

    def check_if_upgrades_available(self, disable_cache: bool = False) -> bool:
        upgradable_resources = self.get_upgradable_resources(disable_cache)
        for provider_name, provider in self.providers.items():
            if len(upgradable_resources[provider.get_provider_name()]) > 0:
                return True
        return False

    def upgrade_resources(self) -> bool:
        if self._resource_cache is None:
            raise Exception("No resources found. Run get_resources() first.")
        if not self.check_if_upgrades_available():
            log.info("No upgrades available.")
            return False
        upgradable_resources = self.get_upgradable_resources()
        for provider_name, resources in upgradable_resources.items():
            for resource in resources:
                try:
                    resource = self.providers[provider_name].patch_resource(resource)
                except Exception as e:
                    log.error(f"Error patching resource '{resource.name}': {e}")
                    resource.set_patch_error()
                    continue
                resource.set_patched()
                if self.repo is not None:
                    log.debug(f"Commiting file: {resource.source_file.absolute().as_posix()} .")
                    self.repo.index.add(resource.source_file.absolute().as_posix())
                    self.repo.index.commit(f"Bump {resource.resource_name} '{resource.name}' from version '{resource.current_version}' to '{resource.newest_version}'.")

        return True

    def print_resource_table(self, only_upgradable: bool, disable_cache: bool = False):
        provider_resources = self.get_resources(disable_cache)
        if len([resource for provider in provider_resources for resource in provider_resources[provider]]) == 0:
            self.console.print("No resources found.")
            return
        if only_upgradable:
            provider_resources = self.get_upgradable_resources(disable_cache)
            if not self.check_if_upgrades_available(disable_cache):
                self.console.print("No upgradable resources found.")
                return

        tables = []
        for provider_name, provider in self.providers.items():
            resources = provider_resources[provider_name]
            if len(resources) > 0:
                tables.append(provider.get_rich_table(resources))
        for table in tables:
            self.console.print(table)

    def _get_statistics(self, disable_cache: bool = False) -> Statistics:
        resources = self.get_resources(disable_cache)
        provider_statistics: dict[str, ProviderStatistics] = {}

        for provider_name, provider in self.providers.items():
            provider_resources = resources[provider.get_provider_name()]
            provider_statistics[provider_name] = ProviderStatistics(
                errors=len([resource for resource in provider_resources if resource.status == ResourceStatus.PATCH_ERROR]),
                resources_patched=len([resource for resource in provider_resources if resource.status == ResourceStatus.PATCHED]),
                resources_pending_update=len([resource for resource in provider_resources if resource.check_if_up_to_date() is False]),
                total_resources=len(provider_resources),
                resources=provider_resources,
            )
        return Statistics(
            errors=sum([provider_statistics[provider].errors for provider in provider_statistics]),
            resources_patched=sum([provider_statistics[provider].resources_patched for provider in provider_statistics]),
            resources_pending_update=sum([provider_statistics[provider].resources_pending_update for provider in provider_statistics]),
            total_resources=sum([provider_statistics[provider].total_resources for provider in provider_statistics]),
            providers=provider_statistics,
        )

    def dump_statistics(self, disable_cache: bool = False):
        if self.statistics_file.exists():
            log.debug(f"Deleting existing statistics file {self.statistics_file.absolute().as_posix()}.")
            self.statistics_file.unlink()
        log.debug(f"Writing statistics to {self.statistics_file.absolute().as_posix()}.")
        statistics_dict = self._get_statistics(disable_cache).to_dict()
        with open(self.statistics_file, "w") as f:
            f.write(json.dumps(statistics_dict))

    def print_statistics_table(self, disable_cache: bool = False):
        table = self._get_statistics(disable_cache).get_rich_table()
        self.console.print(table)

    def get_markdown_tables(self) -> list[MarkdownTableWriter]:
        if self._resource_cache is None:
            raise Exception("No resources found. Run get_resources() first.")

        markdown_tables = []
        for provider_name, provider in self.providers.items():
            changed_resources = [
                resource for resource in self._resource_cache[provider_name] if resource.status == ResourceStatus.PATCHED or resource.status == ResourceStatus.PATCH_ERROR
            ]
            markdown_tables.append(provider.get_markdown_table(changed_resources))
        return markdown_tables

    def set_resources_patched_based_on_existing_resources(self, resources: dict[str, Sequence[VersionedResource]]) -> None:
        for provider_name, provider in self.providers.items():
            current_resources = resources[provider_name]
            for resource in resources[provider_name]:
                current_resource = resource.find(current_resources)
                if len(current_resource) == 0:
                    log.info(f"Resource '{resource.name}' not found in current resources. Skipping.")
                    continue
                if len(current_resource) > 1:
                    raise Exception(f"Found multiple resources with the same name: {resource.name}")
                current_resource[0].set_patched()
