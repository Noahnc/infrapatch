import pytest
from unittest.mock import patch, MagicMock

from infrapatch.core.models.versioned_terraform_resources import TerraformModule, TerraformProvider
from infrapatch.core.utils.terraform.registry_handler import RegistryHandler, ResourceNotFoundException, RegistryMetadataException


@pytest.fixture
def registry_handler():
    default_registry_domain = "testregistry.ch"
    credentials = {"testregistry.ch": "test_token"}
    return RegistryHandler(default_registry_domain, credentials)


def test_get_newest_version_module(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_module_version = {"test/test_module/test_provider": "1.0.0"}

    newest_version = registry_handler.get_newest_version(module)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_not_called()


def test_get_newest_version_provider(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_provider_version = {"test_provider/test_provider": "1.0.0"}

    newest_version = registry_handler.get_newest_version(provider)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_not_called()


def test_get_newest_version_invalid_resource(registry_handler):
    resource = MagicMock()
    with pytest.raises(Exception, match=r"Resource type '<MagicMock.*>' is not supported."):
        registry_handler.get_newest_version(resource)


def test_get_newest_version_module_cached(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_module_version = {"test/test_module/test_provider": "1.0.0"}

    newest_version = registry_handler.get_newest_version(module)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_not_called()


def test_get_newest_version_provider_cached(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_provider_version = {"test_provider/test_provider": "1.0.0"}

    newest_version = registry_handler.get_newest_version(provider)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_not_called()


def test_get_newest_version_module_uncached(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_module_version = {}

    newest_version = registry_handler.get_newest_version(module)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_provider_uncached(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_provider_version = {}

    newest_version = registry_handler.get_newest_version(provider)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_module_no_credentials(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {}

    newest_version = registry_handler.get_newest_version(module)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_provider_no_credentials(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {}

    newest_version = registry_handler.get_newest_version(provider)

    assert newest_version == "1.0.0"
    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_module_not_found(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_module_version = {}

    with patch("infrapatch.core.utils.terraform.registry_handler.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.status = 404

        with pytest.raises(ResourceNotFoundException, match=r"Resource 'test_resource' not found in registry 'testregistry.ch'."):
            registry_handler.get_newest_version(module)

    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_provider_not_found(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_provider_version = {}

    with patch("infrapatch.core.utils.terraform.registry_handler.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.status = 404

        with pytest.raises(ResourceNotFoundException, match=r"Resource 'test_resource' not found in registry 'testregistry.ch'."):
            registry_handler.get_newest_version(provider)

    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_module_error(registry_handler):
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"modules.v1": "https://testregistry.ch/v1/modules"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_module_version = {}

    with patch("infrapatch.core.utils.terraform.registry_handler.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.status = 500

        with pytest.raises(RegistryMetadataException, match=r"Could not get versions from 'https://testregistry.ch/v1/modules/test/test_module/test_provider/versions'."):
            registry_handler.get_newest_version(module)

    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_newest_version_provider_error(registry_handler):
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider")
    registry_handler.get_registry_metadata = MagicMock(return_value={"providers.v1": "https://testregistry.ch/v1/providers"})
    registry_handler.credentials = {"testregistry.ch": "test_token"}
    registry_handler.cached_provider_version = {}

    with patch("infrapatch.core.utils.terraform.registry_handler.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.status = 500

        with pytest.raises(RegistryMetadataException, match=r"Could not get versions from 'https://testregistry.ch/v1/providers/test_provider/test_provider/versions'."):
            registry_handler.get_newest_version(provider)

    registry_handler.get_registry_metadata.assert_called_once_with("testregistry.ch")


def test_get_registry_metadata_cached(registry_handler):
    registry_handler.cached_registry_metadata = {"testregistry.ch": {"modules.v1": "https://testregistry.ch/v1/modules"}}

    metadata = registry_handler.get_registry_metadata("testregistry.ch")

    assert metadata == {"modules.v1": "https://testregistry.ch/v1/modules"}


def test_get_registry_metadata_uncached(registry_handler):
    registry_handler.cached_registry_metadata = {}

    with patch("infrapatch.core.utils.terraform.registry_handler.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.status = 200
        mock_urlopen.return_value.read.return_value = b'{"modules.v1": "https://testregistry.ch/v1/modules"}'

        metadata = registry_handler.get_registry_metadata("testregistry.ch")

    assert metadata == {"modules.v1": "https://testregistry.ch/v1/modules"}
    registry_handler.cached_registry_metadata == {"testregistry.ch": {"modules.v1": "https://testregistry.ch/v1/modules"}}
