import json
import logging as log
from distutils.version import StrictVersion
from typing import Protocol
from urllib import request
from urllib.parse import urlparse

from infrapatch.core.models.versioned_terraform_resources import VersionedTerraformResource, TerraformModule, TerraformProvider


class RegistryNotFoundException(Exception):
    pass


class RegistryMetadataException(Exception):
    pass


class ResourceNotFoundException(Exception):
    pass


class RegistryHandlerInterface(Protocol):
    def get_newest_version(self, resource: VersionedTerraformResource):
        ...


class RegistryHandler(RegistryHandlerInterface):
    def __init__(self, default_registry_domain: str, credentials: dict):
        self.default_registry_domain = default_registry_domain
        self.cached_registry_metadata = {}
        self.cached_module_version = {}
        self.cached_provider_version = {}
        self.credentials = credentials

    def get_newest_version(self, resource: VersionedTerraformResource):
        if not isinstance(resource, TerraformModule) and not isinstance(resource, TerraformProvider):
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        if isinstance(resource, TerraformModule):
            if resource.source in self.cached_module_version:
                log.debug(f"Module versions for '{resource.source}' already cached.")
                return self.cached_module_version[resource.source]

        elif isinstance(resource, TerraformProvider):
            if resource.source in self.cached_provider_version:
                log.debug(f"Provider versions for '{resource.source}' already cached.")
                return self.cached_provider_version[resource.source]

        registry_base_domain = self.default_registry_domain
        if resource.base_domain is not None:
            registry_base_domain = resource.base_domain
        registry_metadata = self.get_registry_metadata(registry_base_domain)

        if isinstance(resource, TerraformModule):
            metadata_key = "modules.v1"
        elif isinstance(resource, TerraformProvider):
            metadata_key = "providers.v1"
        else:
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        version_url = urlparse(registry_metadata[metadata_key])

        if version_url.hostname is not None:
            version_endpoint = f"https://{version_url.hostname}"
        else:
            version_endpoint = f"https://{registry_base_domain}"

        version_endpoint = f"{version_endpoint}{version_url.path}{resource.identifier}/versions"
        log.debug(f"Getting versions from {version_endpoint}")

        request_object = request.Request(version_endpoint)
        try:
            token = self.credentials[registry_base_domain]
            log.debug(f"Found credentials for registry '{registry_base_domain}', using token: {token[0:5]}...")
            request_object.add_header("Authorization", f"Bearer {token}")
        except KeyError:
            log.debug(f"No credentials found for registry '{registry_base_domain}', using unauthenticated request.")
        response = request.urlopen(request_object)
        if response.status == 404:
            raise ResourceNotFoundException(f"Resource '{resource.name}' not found in registry '{registry_base_domain}'.")
        elif response.status >= 400:
            raise RegistryMetadataException(f"Could not get versions from '{version_endpoint}'.")
        response_data = json.loads(response.read())
        if isinstance(resource, TerraformModule):
            versions = response_data["modules"][0]["versions"]
        elif isinstance(resource, TerraformProvider):
            versions = response_data["versions"]
        else:
            raise Exception(f"Resource type '{type(resource)}' is not supported.")
        sorted_versions = sorted(versions, key=lambda k: StrictVersion(k["version"]), reverse=True)
        newest_version = sorted_versions[0]["version"]

        if isinstance(resource, TerraformModule):
            self.cached_module_version[resource.source] = newest_version
        elif isinstance(resource, TerraformProvider):
            self.cached_provider_version[resource.source] = newest_version

        return newest_version

    def get_registry_metadata(self, registry_base_domain: str):
        if registry_base_domain in self.cached_registry_metadata:
            log.debug(f"Registry metadata for '{registry_base_domain}' already cached.")
            return self.cached_registry_metadata[registry_base_domain]
        discovery_url = f"https://{registry_base_domain}/.well-known/terraform.json"
        log.debug(f"Getting registry metadata from {discovery_url}")
        response = request.urlopen(discovery_url)
        if response.status == 404:
            raise RegistryNotFoundException(f"Registry '{registry_base_domain}' not found.")
        elif response.status >= 400:
            raise RegistryMetadataException(f"Could not get registry metadata from '{discovery_url}'.")
        metadata = json.loads(response.read())
        self.cached_registry_metadata[registry_base_domain] = metadata
        return metadata
