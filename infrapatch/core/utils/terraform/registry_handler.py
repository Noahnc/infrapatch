from dataclasses import dataclass
from typing import Union
import json
import logging as log
from distutils.version import StrictVersion
from typing import Protocol
from urllib import request
from urllib.parse import urlparse


from infrapatch.core.models.versioned_terraform_resources import VersionedTerraformResource, TerraformModule, TerraformProvider


class TerraformRegistryException(Exception):
    pass


class RegistryHandlerInterface(Protocol):
    def get_newest_version(self, resource: VersionedTerraformResource):
        ...

    def get_source(self, resource: VersionedTerraformResource):
        ...


@dataclass
class TerraformRegistryResourceCache:
    newest_version: Union[str, None] = None
    source: Union[str, None] = None


class RegistryHandler(RegistryHandlerInterface):
    def __init__(self, default_registry_domain: str, credentials: dict):
        self.default_registry_domain = default_registry_domain
        self.cached_registry_metadata = {}
        self.module_cache: dict[str, TerraformRegistryResourceCache] = {}
        self.provider_cache: dict[str, TerraformRegistryResourceCache] = {}
        self.credentials = credentials

    def get_newest_version(self, resource: VersionedTerraformResource):
        if not isinstance(resource, TerraformModule) and not isinstance(resource, TerraformProvider):
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        cache = self._get_from_cache(resource)
        if cache.newest_version is not None:
            return cache.newest_version

        registry_api_base_endpoint, registry_base_domain = self._compose_base_url(resource)
        version_endpoint = f"{registry_api_base_endpoint}/versions"
        log.debug(f"Getting versions from {version_endpoint}")

        response = self._send_request(version_endpoint, registry_base_domain)
        response_data = json.loads(response.read())
        if isinstance(resource, TerraformModule):
            versions = response_data["modules"][0]["versions"]
        elif isinstance(resource, TerraformProvider):
            versions = response_data["versions"]
        else:
            raise Exception(f"Resource type '{type(resource)}' is not supported.")
        if len(versions) == 0:
            log.warning(f"No versions found for resource '{resource.source}'.")
            return None
        sorted_versions = sorted(versions, key=lambda k: StrictVersion(k["version"]), reverse=True)
        newest_version = sorted_versions[0]["version"]

        cache.newest_version = newest_version

        return newest_version

    def _get_from_cache(self, resource: VersionedTerraformResource) -> TerraformRegistryResourceCache:
        if isinstance(resource, TerraformModule):
            cache = self.module_cache
        elif isinstance(resource, TerraformProvider):
            cache = self.provider_cache
        else:
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        if resource.source in cache:
            log.debug(f"Cache found for resource {resource.source}.")
            return cache[resource.source]

        log.debug(f"No cache found for resource {resource.source}.")
        new_cache = TerraformRegistryResourceCache()
        cache[resource.source] = new_cache
        return new_cache

    def _compose_base_url(self, resource):
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

        url_from_meta = urlparse(registry_metadata[metadata_key])

        if url_from_meta.hostname is not None:
            endpoint = f"https://{url_from_meta.hostname}"
        else:
            endpoint = f"https://{registry_base_domain}"

        endpoint = f"{endpoint}{url_from_meta.path}{resource.identifier}"
        return endpoint, registry_base_domain

    def get_source(self, resource: VersionedTerraformResource):
        if not isinstance(resource, TerraformModule) and not isinstance(resource, TerraformProvider):
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        cache = self._get_from_cache(resource)
        if cache.source is not None:
            return cache.source

        base_endpoint, registry_base_domain = self._compose_base_url(resource)
        version_info_endpoint = f"{base_endpoint}/{resource.newest_version}"
        try:
            response = self._send_request(version_info_endpoint, registry_base_domain)
        except TerraformRegistryException as e:
            log.debug(f"Could not get source for resource '{resource.source}': {e}")
            return None
        response_data = json.loads(response.read())
        if "source" not in response_data:
            log.debug(f"Source not found in response data: {response_data}")
            return None
        source = response_data["source"]
        log.debug(f"Source for '{resource.source}' is '{source}'")
        cache.source = source
        return source

    def _send_request(self, url: str, registry_base_domain: str):
        request_object = request.Request(url)

        if registry_base_domain in self.credentials:
            token = self.credentials[registry_base_domain]
            log.debug(f"Found credentials for registry '{registry_base_domain}', using token: {token[0:5]}...")
            request_object.add_header("Authorization", f"Bearer {token}")
        else:
            log.debug(f"No credentials found for registry '{registry_base_domain}', using unauthenticated request.")
        try:
            response = request.urlopen(request_object)
        except Exception as e:
            raise TerraformRegistryException(f"Registry request returned an error '{url}': {e}")
        if response.status == 404:
            raise TerraformRegistryException(f"Registry resource '{url}' not found.")
        elif response.status >= 400:
            raise TerraformRegistryException(f"Registry request '{url}' returned error code '{response.status}'.")
        return response

    def get_registry_metadata(self, registry_base_domain: str):
        if registry_base_domain in self.cached_registry_metadata:
            log.debug(f"Registry metadata for '{registry_base_domain}' already cached.")
            return self.cached_registry_metadata[registry_base_domain]
        discovery_url = f"https://{registry_base_domain}/.well-known/terraform.json"
        response = self._send_request(discovery_url, registry_base_domain)
        metadata = json.loads(response.read())
        self.cached_registry_metadata[registry_base_domain] = metadata
        return metadata
