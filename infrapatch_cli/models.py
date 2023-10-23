import logging as log
import re
from dataclasses import dataclass
from distutils.version import StrictVersion
from pathlib import Path
from typing import Optional


@dataclass
class VersionedTerraformResource:
    name: str
    current_version: str
    source_file: Path
    newest_version: str = None
    _base_domain: str = None
    _identifier: str = None
    _source: str = None

    @property
    def source(self) -> str:
        return self._source

    @property
    def base_domain(self) -> Optional[str]:
        return self._base_domain

    @property
    def resource_name(self):
        raise NotImplementedError()

    @property
    def identifier(self) -> str:
        return self._identifier

    def set_newest_version(self, version: str):
        self.newest_version = version

    def installed_version_equal_or_newer_than_new_version(self):
        if self.newest_version is None:
            raise Exception(f"Newest version of resource '{self.name}' is not set.")
        if StrictVersion(self.newest_version) > StrictVersion(self.current_version):
            return False
        return True


@dataclass
class TerraformModule(VersionedTerraformResource):

    def __post_init__(self):
        self.source = self._source

    @property
    def source(self) -> str:
        return self._source

    @property
    def resource_name(self):
        return "Module"

    @source.setter
    def source(self, source: str):
        source_lower_case = source.lower()
        self._source = source_lower_case
        self.newest_version = None
        if re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from a generic registry.")
            self._base_domain = source_lower_case.split("/")[0]
            self._identifier = "/".join(source_lower_case.split("/")[1:])
        elif re.match(r"^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(
                f"Source '{source_lower_case}' is from the public registry.")
            self._identifier = source_lower_case
        else:
            raise Exception(f"Source '{source_lower_case}' is not a valid terraform resource source.")


@dataclass
class TerraformProvider(VersionedTerraformResource):

    def __post_init__(self):
        self.source = self._source

    @property
    def source(self) -> str:
        return self._source

    @property
    def resource_name(self):
        return "Module"

    @source.setter
    def source(self, source: str) -> None:
        source_lower_case = source.lower()
        self._source = source_lower_case
        self.newest_version = None
        if re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from a generic registry.")
            self._base_domain = source_lower_case.split("/")[0]
            self._identifier = "/".join(source_lower_case.split("/")[1:])
        elif re.match(r"^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(
                f"Source '{source_lower_case}' is from the public registry.")
            self._identifier = source_lower_case
        else:
            raise Exception(f"Source '{source_lower_case}' is not a valid terraform resource source.")


def get_upgradable_resources(resources: list[VersionedTerraformResource]) -> list[VersionedTerraformResource]:
    return [resource for resource in resources if not resource.installed_version_equal_or_newer_than_new_version()]