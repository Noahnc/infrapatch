import logging as log
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import semantic_version
from git import Sequence
from pydantic import BaseModel


class ResourceStatus:
    UNPATCHED = "unpatched"
    UP_TO_DATE = "up_to_date"
    PATCHED = "patched"
    PATCH_ERROR = "patch_error"
    NO_VERSION_FOUND = "no_version_found"


class VersionedResourceOptions(BaseModel):
    ignore_resource: bool = False


class VersionedResource(BaseModel):
    name: str
    current_version: str
    start_line_number: int
    source_file: Path
    newest_version_string: Optional[str] = None
    status: str = ResourceStatus.UNPATCHED
    github_repo_string: Optional[str] = None
    options: VersionedResourceOptions = VersionedResourceOptions()

    @property
    def resource_name(self):
        raise NotImplementedError()

    @property
    def newest_version_base(self):
        if self.has_tile_constraint():
            if self.newest_version_string is None:
                raise Exception(f"Newest version of resource '{self.name}' is not set.")
            return self.newest_version_string.strip("~>")
        return self.newest_version_string

    @property
    def newest_version(self):
        return self.newest_version_string

    @newest_version.setter
    def newest_version(self, version: Optional[str]):
        if self.has_tile_constraint():
            self.newest_version_string = f"~>{version}"
        else:
            self.newest_version_string = version

        if version is None:
            self.set_no_version_found()
            return

        if self.installed_version_equal_or_newer_than_new_version():
            self.set_up_to_date()

    @property
    def github_repo(self):
        return self.github_repo_string

    @github_repo.setter
    def github_repo(self, github_repo_url: str):
        url = urlparse(github_repo_url)
        if url.path is None or url.path == "" or url.path == "/":
            raise Exception(f"Invalid github repo url '{github_repo_url}'.")
        path = url.path
        if path.endswith(".git"):
            path = path[:-4]
        repo = "/".join(path.split("/")[1:3])
        log.debug(f"Setting github repo for resource '{self.name}' to '{repo}'")
        self.github_repo_string = repo

    def set_patched(self):
        self.status = ResourceStatus.PATCHED

    def set_no_version_found(self):
        self.status = ResourceStatus.NO_VERSION_FOUND

    def set_up_to_date(self):
        self.status = ResourceStatus.UP_TO_DATE

    def has_tile_constraint(self) -> bool:
        result = re.match(r"^~>[0-9]+\.[0-9]+\.[0-9]+$", self.current_version)
        if result is None:
            return False
        return True

    def set_patch_error(self):
        self.status = ResourceStatus.PATCH_ERROR

    def find(self, resources):
        result = [resource for resource in resources if resource.name == self.name and resource.source_file == self.source_file]
        return result

    def installed_version_equal_or_newer_than_new_version(self):
        if self.status == ResourceStatus.NO_VERSION_FOUND:
            return True
        if self.newest_version_string is None:
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
        return self.model_dump()


class VersionedResourceReleaseNotes(BaseModel):
    resources: Sequence[VersionedResource]
    name: str
    body: str
    version: str
