import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import semantic_version


class ResourceStatus:
    UNPATCHED = "unpatched"
    PATCHED = "patched"
    PATCH_ERROR = "patch_error"


@dataclass
class VersionedResource:
    name: str
    current_version: str
    _source_file: str
    _newest_version: Union[str, None] = None
    _status: str = ResourceStatus.UNPATCHED

    @property
    def source_file(self) -> Path:
        return Path(self._source_file)

    @property
    def status(self) -> str:
        return self._status

    @property
    def resource_name(self):
        raise NotImplementedError()

    @property
    def newest_version(self) -> Optional[str]:
        return self._newest_version

    @property
    def newest_version_base(self):
        if self.has_tile_constraint():
            if self.newest_version is None:
                raise Exception(f"Newest version of resource '{self.name}' is not set.")
            return self.newest_version.strip("~>")
        return self.newest_version

    @newest_version.setter
    def newest_version(self, version: str):
        if self.has_tile_constraint():
            self._newest_version = f"~>{version}"
            return
        self._newest_version = version

    def set_patched(self):
        self._status = ResourceStatus.PATCHED

    def has_tile_constraint(self) -> bool:
        result = re.match(r"^~>[0-9]+\.[0-9]+\.[0-9]+$", self.current_version)
        if result is None:
            return False
        return True

    def set_patch_error(self):
        self._status = ResourceStatus.PATCH_ERROR

    def find(self, resources):
        result = [resource for resource in resources if resource.name == self.name and resource._source_file == self._source_file]
        return result

    def installed_version_equal_or_newer_than_new_version(self):
        if self.newest_version is None:
            raise Exception(f"Newest version of resource '{self.name}' is not set.")

        newest = semantic_version.Version(self.newest_version_base)

        # check if the current version has the following format: "1.2.3"
        if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", self.current_version):
            current = semantic_version.Version(self.current_version)
            if current >= newest:
                return True
            return False

        # chech if the current version has the following format: "~>3.76.0"
        if self.has_tile_constraint():
            current = semantic_version.Version(self.current_version.strip("~>"))
            if current.major > newest.major:  # type: ignore
                return True
            if current.minor >= newest.minor:  # type: ignore
                return True
            return False

        current_constraint = semantic_version.NpmSpec(self.current_version)
        if newest in current_constraint:
            return True
        return False

    def check_if_up_to_date(self):
        if self.status == ResourceStatus.PATCH_ERROR:
            return False
        if self.status == ResourceStatus.PATCHED:
            return True
        if self.installed_version_equal_or_newer_than_new_version():
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
