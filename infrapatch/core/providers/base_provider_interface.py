from typing import Protocol, Sequence
from pytablewriter import MarkdownTableWriter
from rich.table import Table
from infrapatch.core.models.versioned_resource import VersionedResource


class BaseProviderInterface(Protocol):
    def get_provider_name(self) -> str:
        ...

    def get_provider_display_name(self) -> str:
        ...

    def get_resources(self) -> Sequence[VersionedResource]:
        ...

    def patch_resource(self, resource: VersionedResource) -> VersionedResource:
        ...

    def get_rich_table(self, resources: Sequence[VersionedResource]) -> Table:
        ...

    def get_markdown_table(self, resources: Sequence[VersionedResource]) -> MarkdownTableWriter:
        ...

    def get_resources_as_dict_list(self, resources: Sequence[VersionedResource]):
        ...
