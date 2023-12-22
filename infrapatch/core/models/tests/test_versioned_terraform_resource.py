from pathlib import Path, PosixPath

import pytest

from infrapatch.core.models.versioned_terraform_resources import TerraformModule, TerraformProvider


def test_attributes():
    # test with default registry
    module = TerraformModule(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="test/test_module/test_provider", start_line_number=1)
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="test_provider/test_provider", start_line_number=1)

    assert module.source == "test/test_module/test_provider"
    assert module.base_domain is None
    assert module.identifier == "test/test_module/test_provider"

    assert provider.source == "test_provider/test_provider"
    assert provider.base_domain is None
    assert provider.identifier == "test_provider/test_provider"

    # test with custom registry
    module = TerraformModule(
        name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="testregistry.ch/test/test_module/test_provider", start_line_number=1
    )
    provider = TerraformProvider(
        name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="testregistry.ch/test_provider/test_provider", start_line_number=1
    )

    assert module.source == "testregistry.ch/test/test_module/test_provider"
    assert module.base_domain == "testregistry.ch"
    assert module.identifier == "test/test_module/test_provider"

    assert provider.source == "testregistry.ch/test_provider/test_provider"
    assert provider.base_domain == "testregistry.ch"
    assert provider.identifier == "test_provider/test_provider"

    # test invalid sources
    with pytest.raises(Exception):
        TerraformModule(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="test/test_module/test_provider/test", start_line_number=1)
        TerraformModule(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="/test_module", start_line_number=1)

    with pytest.raises(Exception):
        TerraformProvider(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="/test_module", start_line_number=1)
        TerraformProvider(
            name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="kfdsjflksdj/kldfsjflsdkj/dkljflsk/test_module", start_line_number=1
        )


def test_find():
    findably_resource = TerraformModule(
        name="test_resource3", current_version="1.0.0", source_file=Path("test_file3.py"), source_string="test/test_module3/test_provider", start_line_number=1
    )
    unfindably_resource = TerraformModule(
        name="test_resource6", current_version="1.0.0", source_file=Path("test_file8.py"), source_string="test/test_module3/test_provider", start_line_number=1
    )
    resources = [
        TerraformModule(name="test_resource1", current_version="1.0.0", source_file=Path("test_file1.py"), source_string="test/test_module1/test_provider", start_line_number=1),
        TerraformModule(name="test_resource2", current_version="1.0.0", source_file=Path("test_file2.py"), source_string="test/test_module2/test_provider", start_line_number=1),
        TerraformModule(name="test_resource3", current_version="1.0.0", source_file=Path("test_file3.py"), source_string="test/test_module3/test_provider", start_line_number=1),
        TerraformModule(name="test_resource4", current_version="1.0.0", source_file=Path("test_file4.py"), source_string="test/test_module4/test_provider", start_line_number=1),
        TerraformModule(name="test_resource5", current_version="1.0.0", source_file=Path("test_file5.py"), source_string="test/test_module5/test_provider", start_line_number=1),
    ]
    assert len(findably_resource.find(resources)) == 1
    assert findably_resource.find(resources) == [resources[2]]
    assert len(unfindably_resource.find(resources)) == 0


def test_to_dict():
    module = TerraformModule(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="test/test_module/test_provider", start_line_number=1)
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), source_string="test_provider/test_provider", start_line_number=1)

    module_dict = module.model_dump()
    provider_dict = provider.model_dump()

    assert module_dict == {
        "name": "test_resource",
        "current_version": "1.0.0",
        "newest_version_string": None,
        "status": "unpatched",
        "source_file": PosixPath("test_file.py"),
        "source_string": "test/test_module/test_provider",
        "base_domain": None,
        "identifier": "test/test_module/test_provider",
        "github_repo_string": None,
        "start_line_number": 1,
        "options": {
            "ignore_resource": False,
        },
    }
    assert provider_dict == {
        "name": "test_resource",
        "current_version": "1.0.0",
        "newest_version_string": None,
        "status": "unpatched",
        "source_file": PosixPath("test_file.py"),
        "source_string": "test_provider/test_provider",
        "base_domain": None,
        "identifier": "test_provider/test_provider",
        "github_repo_string": None,
        "start_line_number": 1,
        "options": {
            "ignore_resource": False,
        },
    }
