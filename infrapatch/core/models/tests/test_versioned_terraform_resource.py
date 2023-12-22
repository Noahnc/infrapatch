import pytest

from infrapatch.core.models.versioned_terraform_resources import TerraformModule, TerraformProvider


def test_attributes():
    # test with default registry
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=1)
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider", start_line_number=1)

    assert module.source == "test/test_module/test_provider"
    assert module.base_domain is None
    assert module.identifier == "test/test_module/test_provider"

    assert provider.source == "test_provider/test_provider"
    assert provider.base_domain is None
    assert provider.identifier == "test_provider/test_provider"

    # test with custom registry
    module = TerraformModule(
        name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="testregistry.ch/test/test_module/test_provider", start_line_number=1
    )
    provider = TerraformProvider(
        name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="testregistry.ch/test_provider/test_provider", start_line_number=1
    )

    assert module.source == "testregistry.ch/test/test_module/test_provider"
    assert module.base_domain == "testregistry.ch"
    assert module.identifier == "test/test_module/test_provider"

    assert provider.source == "testregistry.ch/test_provider/test_provider"
    assert provider.base_domain == "testregistry.ch"
    assert provider.identifier == "test_provider/test_provider"

    # test invalid sources
    with pytest.raises(Exception):
        TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider/test", start_line_number=1)
        TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="/test_module", start_line_number=1)

    with pytest.raises(Exception):
        TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="/test_module", start_line_number=1)
        TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="kfdsjflksdj/kldfsjflsdkj/dkljflsk/test_module", start_line_number=1)


def test_find():
    findably_resource = TerraformModule(
        name="test_resource3", current_version="1.0.0", _source_file="test_file3.py", _source="test/test_module3/test_provider", start_line_number=1
    )
    unfindably_resource = TerraformModule(
        name="test_resource6", current_version="1.0.0", _source_file="test_file8.py", _source="test/test_module3/test_provider", start_line_number=1
    )
    resources = [
        TerraformModule(name="test_resource1", current_version="1.0.0", _source_file="test_file1.py", _source="test/test_module1/test_provider", start_line_number=1),
        TerraformModule(name="test_resource2", current_version="1.0.0", _source_file="test_file2.py", _source="test/test_module2/test_provider", start_line_number=1),
        TerraformModule(name="test_resource3", current_version="1.0.0", _source_file="test_file3.py", _source="test/test_module3/test_provider", start_line_number=1),
        TerraformModule(name="test_resource4", current_version="1.0.0", _source_file="test_file4.py", _source="test/test_module4/test_provider", start_line_number=1),
        TerraformModule(name="test_resource5", current_version="1.0.0", _source_file="test_file5.py", _source="test/test_module5/test_provider", start_line_number=1),
    ]
    assert len(findably_resource.find(resources)) == 1
    assert findably_resource.find(resources) == [resources[2]]
    assert len(unfindably_resource.find(resources)) == 0


def test_to_dict():
    module = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=1)
    provider = TerraformProvider(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test_provider/test_provider", start_line_number=1)

    module_dict = module.to_dict()
    provider_dict = provider.to_dict()

    assert module_dict == {
        "name": "test_resource",
        "current_version": "1.0.0",
        "_newest_version": None,
        "_status": "unpatched",
        "_source_file": "test_file.py",
        "_source": "test/test_module/test_provider",
        "_base_domain": None,
        "_identifier": "test/test_module/test_provider",
        "_github_repo": None,
        "start_line_number": 1,
        "options": None,
    }
    assert provider_dict == {
        "name": "test_resource",
        "current_version": "1.0.0",
        "_newest_version": None,
        "_status": "unpatched",
        "_source_file": "test_file.py",
        "_source": "test_provider/test_provider",
        "_base_domain": None,
        "_identifier": "test_provider/test_provider",
        "_github_repo": None,
        "start_line_number": 1,
        "options": None,
    }
