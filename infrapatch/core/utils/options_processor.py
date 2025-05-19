import logging as log
from typing import Any, Protocol, Union
import infrapatch.core.constants as cs

from infrapatch.core.models.versioned_resource import VersionedResource, VersionedResourceOptions


class OptionsProcessorInterface(Protocol):
    def process_options_for_resource(self, resource: VersionedResource) -> VersionedResource: ...


class OptionsProcessor(OptionsProcessorInterface):
    def _get_upper_line_content(self, resource: VersionedResource) -> Union[str, None]:
        if resource.start_line_number == 0:
            raise Exception(f"Resource '{resource.name}' has invalid start line number 0.")
        if resource.start_line_number == 1:
            return None
        with open(resource.source_file, "r") as f:
            lines = f.readlines()
            return lines[resource.start_line_number - 2].strip()

    def _process_options_string(self, options: str) -> dict[str, Any]:
        options_dict = {}
        for option in options.split(","):
            key, value = option.split("=")
            options_dict[key.strip()] = value.strip()
        return options_dict

    def _get_options_object(self, line: str) -> VersionedResourceOptions:
        # Get the rigth part of the options line
        options_string = line.split(cs.infrapatch_options_prefix)[1].strip()
        optioons_dict = self._process_options_string(options_string)
        return VersionedResourceOptions(**optioons_dict)

    def process_options_for_resource(self, resource: VersionedResource) -> VersionedResource:
        upper_line_content = self._get_upper_line_content(resource)

        if upper_line_content is None:
            log.debug(f"Resource '{resource.name}' has no options.")
            return resource

        if cs.infrapatch_options_prefix not in upper_line_content:
            log.debug(f"Resource '{resource.name}' has no options.")
            return resource

        resource.options = self._get_options_object(upper_line_content)
        return resource
