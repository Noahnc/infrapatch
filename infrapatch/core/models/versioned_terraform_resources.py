import logging as log
import re
import semantic_version
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union


class ResourceStatus:
    UNPATCHED = "unpatched"
    PATCHED = "patched"
    PATCH_ERROR = "patch_error"


@dataclass
class VersionedTerraformResource:
    name: str
    current_version: str
    source_file: Path
    _newest_version: Union[str, None] = None
    _status: str = ResourceStatus.UNPATCHED
    _base_domain: Union[str, None] = None
    _identifier: Union[str, None] = None
    _source: Union[str, None] = None

    @property
    def source(self) -> Union[str, None]:
        return self._source

    @property
    def status(self) -> str:
        return self._status

    @property
    def base_domain(self) -> Optional[str]:
        return self._base_domain

    @property
    def resource_name(self):
        raise NotImplementedError()

    @property
    def identifier(self) -> Union[str, None]:
        return self._identifier

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

    def has_tile_constraint(self):
        return re.match(r"^~>[0-9]+\.[0-9]+\.[0-9]+$", self.current_version)

    def set_patch_error(self):
        self._status = ResourceStatus.PATCH_ERROR

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
            if current.major > newest.major: # type: ignore
                return True
            if current.minor >= newest.minor: # type: ignore
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

    def __to_dict__(self):
        return {
            "name": self.name,
            "current_version": self.current_version,
            "source_file": self.source_file.absolute().as_posix(),
            "newest_version": self.newest_version,
            "status": self.status,
            "base_domain": self.base_domain,
            "identifier": self.identifier,
            "source": self.source
        }


@dataclass
class TerraformModule(VersionedTerraformResource):

    def __post_init__(self):
        if self._source is None:
            raise Exception("Source is None.")
        self.source = self._source

    @property
    def source(self) -> Union[str, None]:
        return self._source

    @property
    def resource_name(self):
        return "Module"

    @source.setter
    def source(self, source: str):
        source_lower_case = source.lower()
        self._source = source_lower_case
        self._newest_version = None
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
        if self._source is None:
            raise Exception("Source is None.")
        self.source = self._source

    @property
    def source(self) -> Union[str, None]:
        return self._source

    @property
    def resource_name(self):
        return "Module"

    @source.setter
    def source(self, source: str) -> None:
        source_lower_case = source.lower()
        self._source = source_lower_case
        self._newest_version = None
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


def get_upgradable_resources(resources: Sequence[VersionedTerraformResource]) -> Sequence[VersionedTerraformResource]:
    return [resource for resource in resources if not resource.check_if_up_to_date()]


def from_terraform_resources_to_dict_list(terraform_resources: Sequence[VersionedTerraformResource]) -> Sequence[dict]:
    return [terraform_resource.__to_dict__() for terraform_resource in terraform_resources]
