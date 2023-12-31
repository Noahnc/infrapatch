import logging as log
from pathlib import Path
from typing import Sequence, Union

from git import Repo
from pytablewriter import MarkdownTableWriter
from rich import progress
from rich.console import Console

from infrapatch.core.models.statistics import ProviderStatistics, Statistics
from infrapatch.core.models.versioned_resource import ResourceStatus, VersionedResource, VersionedResourceReleaseNotes
from infrapatch.core.providers.base_provider_interface import BaseProviderInterface
from infrapatch.core.utils.options_processor import OptionsProcessorInterface


class ProviderHandler:
    def __init__(
        self, providers: Sequence[BaseProviderInterface], console: Console, statistics_file: Path, options_processor: OptionsProcessorInterface, repo: Union[Repo, None] = None
    ) -> None:
        self.providers: dict[str, BaseProviderInterface] = {}
        for provider in providers:
            self.providers[provider.get_provider_name()] = provider

        self._resource_cache: dict[str, Sequence[VersionedResource]] = {}
        self.console = console
        self.statistics_file = statistics_file
        self.repo = repo
        self.options_processor = options_processor

    def get_resources(self, disable_cache: bool = False) -> dict[str, Sequence[VersionedResource]]:
        for provider_name, provider in self.providers.items():
            if provider_name not in self._resource_cache:
                log.debug(f"Fetching resources for provider {provider.get_provider_name()} since cache is empty.")
            elif disable_cache:
                log.debug(f"Fetching resources for provider {provider.get_provider_name()} since cache is disabled.")
            else:
                log.debug(f"Using cached resources for provider {provider.get_provider_name()}.")
                continue
            resources = provider.get_resources()
            for resource in resources:
                self.options_processor.process_options_for_resource(resource)
            ignored_resources = [resource for resource in resources if resource.options.ignore_resource]
            un_ignored_resources = [resource for resource in resources if not resource.options.ignore_resource]
            for resource in ignored_resources:
                log.debug(f"Ignoring resource '{resource.name}' from provider {provider.get_provider_display_name()}since its marked as ignored.")

            self._resource_cache[provider.get_provider_name()] = un_ignored_resources
        return self._resource_cache

    def get_patched_resources(self) -> dict[str, Sequence[VersionedResource]]:
        resources = self.get_resources()
        patched_resources: dict[str, Sequence[VersionedResource]] = {}
        for provider_name, provider in self.providers.items():
            patched_resources[provider.get_provider_name()] = [resource for resource in resources[provider_name] if resource.status == ResourceStatus.PATCHED]
        return patched_resources

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
            for resource in progress.track(resources, description=f"Upgrading resources for Provider {self.providers[provider_name].get_provider_display_name()}..."):
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
        statistics = self._get_statistics(disable_cache)
        with open(self.statistics_file, "w") as f:
            f.write(statistics.model_dump_json())

    def print_statistics_table(self, disable_cache: bool = False):
        table = self._get_statistics(disable_cache).get_rich_table()
        self.console.print(table)

    def get_markdown_table_for_changed_resources(self) -> dict[str, MarkdownTableWriter]:
        if self._resource_cache is None:
            raise Exception("No resources found. Run get_resources() first.")

        markdown_tables = {}
        for provider_name, provider in self.providers.items():
            changed_resources = [
                resource for resource in self._resource_cache[provider_name] if resource.status == ResourceStatus.PATCHED or resource.status == ResourceStatus.PATCH_ERROR
            ]
            if len(changed_resources) == 0:
                log.debug(f"No changed resources found for provider {provider_name}. Skipping.")
                continue
            markdown_tables[provider_name] = provider.get_markdown_table(changed_resources)
        return markdown_tables

    def set_resources_patched_based_on_existing_resources(self, original_resources: dict[str, Sequence[VersionedResource]]) -> None:
        for provider_name, provider in self.providers.items():
            original_resources_provider = original_resources[provider_name]
            for i, resource in enumerate(self._resource_cache[provider_name]):
                found_resources = resource.find(original_resources_provider)
                if len(found_resources) == 0:
                    log.debug(f"Resource '{resource.name}' not found in original resources. Skipping update.")
                    continue
                if len(found_resources) > 1:
                    raise Exception(f"Found multiple resources with the same name: {resource.name}")
                log.debug(f"Updating resource '{resource.name}' from provider {provider_name} with original resource.")
                found_resource = found_resources[0]
                found_resource.set_patched()
                self._resource_cache[provider_name][i] = found_resource  # type: ignore

    def get_release_notes(self, resources: dict[str, Sequence[VersionedResource]]) -> dict[str, Sequence[VersionedResourceReleaseNotes]]:
        release_notes: dict[str, Sequence[VersionedResourceReleaseNotes]] = {}
        for provider_name, provider in self.providers.items():
            provider_release_notes: list[VersionedResourceReleaseNotes] = []
            patched_resources = [resource for resource in resources[provider_name] if resource.status == ResourceStatus.PATCHED]
            grouped_resources = provider.get_grouped_by_identifier(patched_resources)
            for identifier in progress.track(grouped_resources, description=f"Getting release notes for resources of Provider {provider.get_provider_display_name()}..."):
                identifier_resources = grouped_resources[identifier]
                if identifier_resources[0].status == ResourceStatus.NO_VERSION_FOUND:
                    log.debug(f"Skipping resource '{identifier_resources[0].name}' since no version was found.")
                    continue
                resource_release_note = provider.get_resource_release_notes(grouped_resources[identifier][0])
                if resource_release_note is not None:
                    resource_release_note.resources = grouped_resources[identifier]
                    provider_release_notes.append(resource_release_note)
            release_notes[provider_name] = provider_release_notes
        return release_notes
