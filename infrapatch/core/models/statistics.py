from dataclasses import dataclass
import dataclasses
from typing import Any, Sequence
from pytablewriter import MarkdownTableWriter
from rich.table import Table
from infrapatch.core.models.versioned_resource import VersionedResource


@dataclass
class BaseStatistics:
    errors: int
    resources_patched: int
    resources_pending_update: int
    total_resources: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ProviderStatistics(BaseStatistics):
    resources: Sequence[VersionedResource]


@dataclass
class Statistics(BaseStatistics):
    providers: dict[str, ProviderStatistics]

    def get_rich_table(self) -> Table:
        table = Table(show_header=True, title="Statistics", expand=True)
        table.add_column("Errors")
        table.add_column("Patched")
        table.add_column("Pending Update")
        table.add_column("Total")
        table.add_column("Enabled Providers")
        table.add_row(
            str(self.errors),
            str(self.resources_patched),
            str(self.resources_pending_update),
            str(self.total_resources),
            str(len(self.providers)),
        )
        return table

    def get_markdown_table(self) -> MarkdownTableWriter:
        dict_element = {
            "Errors": self.errors,
            "Patched": self.resources_patched,
            "Pending Update": self.resources_pending_update,
            "Total": self.total_resources,
            "Enabled Providers": len(self.providers),
        }
        return MarkdownTableWriter(
            table_name="Statistics",
            headers=list(dict_element.keys()),
            value_matrix=[list(dict_element.values())],
        )
