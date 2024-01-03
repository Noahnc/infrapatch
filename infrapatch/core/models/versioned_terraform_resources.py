import logging as log
import re
from typing import Optional

from infrapatch.core.models.versioned_resource import VersionedResource


class VersionedTerraformResource(VersionedResource):
    source_string: str
    base_domain: Optional[str] = None
    identifier: Optional[str] = None

    @property
    def source(self) -> str:
        if self.source_string is None:
            raise Exception("Source is None.")
        return self.source_string

    @property
    def resource_name(self):
        raise NotImplementedError()

    def find(self, resources):
        filtered_resources = super().find(resources)
        return [resource for resource in filtered_resources if resource.source == self.source]


class TerraformModule(VersionedTerraformResource):
    def model_post_init(self, __context):
        self.source = self.source_string

    @property
    def source(self) -> str:
        return self.source_string

    @property
    def resource_name(self):
        return "Terraform Module"

    @source.setter
    def source(self, source: str):
        source_lower_case = source.lower()
        self.source_string = source_lower_case
        self.newest_version_string = None
        if re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from a generic registry.")
            self.base_domain = source_lower_case.split("/")[0]
            self.identifier = "/".join(source_lower_case.split("/")[1:])
        elif re.match(r"^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from the public registry.")
            self.identifier = source_lower_case
        else:
            raise Exception(f"Source '{source_lower_case}' is not a valid terraform resource source.")


class TerraformProvider(VersionedTerraformResource):
    def model_post_init(self, __context):
        self.source = self.source_string

    @property
    def source(self) -> str:
        return self.source_string

    @property
    def resource_name(self):
        return "Terraform Provider"

    @source.setter
    def source(self, source: str) -> None:
        source_lower_case = source.lower()
        self.source_string = source_lower_case
        self.newest_version_string = None
        if re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+/[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from a generic registry.")
            self.base_domain = source_lower_case.split("/")[0]
            self.identifier = "/".join(source_lower_case.split("/")[1:])
        elif re.match(r"^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$", source_lower_case):
            log.debug(f"Source '{source_lower_case}' is from the public registry.")
            self.identifier = source_lower_case
        else:
            raise Exception(f"Source '{source_lower_case}' is not a valid terraform resource source.")
