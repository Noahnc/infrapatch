from pathlib import Path
from unittest.mock import patch

import pytest

from infrapatch.core.models.versioned_terraform_resources import TerraformModule, TerraformProvider
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli
from infrapatch.core.utils.terraform.hcl_handler import HclHandler, HclParserException


@pytest.fixture
def tmp_user_home(tmp_path: Path):
    return tmp_path


@pytest.fixture
def hcl_handler(tmp_user_home: Path):
    return HclHandler(hcl_edit_cli=HclEditCli())


@pytest.fixture
def valid_terraform_code():
    return """
        terraform {
            required_providers {
                test_provider = {
                    source = "test_provider/test_provider"
                    version = ">1.0.0"
                }
                test_provider2 = {
                    source = "spacelift.io/test_provider/test_provider2"
                    version = "1.0.5"
                }
            }
        }
        module "test_module" {
            source = "test/test_module/test_provider"
            version = "2.0.0"
            name = "Test_module"
        }
        module "test_module2" {
            source = "spacelift.io/test/test_module/test_provider"
            version = "1.0.2"
            name = "Test_module2"
        }
        # This module should be ignored since it has no version
        module "test_module3" {
            source = "C:/test/test_module/test_provider"
            name = "Test_module3"
        }
    """


@pytest.fixture
def invalid_terraform_code():
    return """
        terraform {
            required_providers {
                test_provider = {
                    source = "test_provider/test_provider"
                    version = ">1.0.0"
                }
                test_provider = {
                    source = "spacelift.io/test_provider/test_provider2"
                    version = "1.0.5
                }
            }
        }
        module "test_module" {
            source = "test/test_module/test_provider"
            version = "2.0.0"
            name = Test_module"
            }
        }
    """


def test_get_terraform_resources_from_file(hcl_handler: HclHandler, valid_terraform_code: str, tmp_path: Path):
    # Create a temporary Terraform file for testing
    tf_file = tmp_path.joinpath("test_file.tf")
    tf_file.write_text(valid_terraform_code)
    resouces = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=True)
    modules = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=False)
    providers = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=False, get_providers=True)

    modules_filtered = [resource for resource in resouces if isinstance(resource, TerraformModule)]
    providers_filtered = [resource for resource in resouces if isinstance(resource, TerraformProvider)]

    assert len(resouces) == 4
    assert len(modules) == 2
    assert len(providers) == 2
    assert len(modules_filtered) == len(modules)
    assert len(providers_filtered) == len(providers)

    for resource in resouces:
        assert resource._source_file == tf_file.absolute().as_posix()
        if resource.name == "test_module":
            assert isinstance(resource, TerraformModule)
            assert resource.current_version == "2.0.0"
            assert resource.source == "test/test_module/test_provider"
            assert resource.identifier == "test/test_module/test_provider"
            assert resource.start_line_number == 14
            assert resource.base_domain is None
        elif resource.name == "test_module2":
            assert isinstance(resource, TerraformModule)
            assert resource.current_version == "1.0.2"
            assert resource.source == "spacelift.io/test/test_module/test_provider"
            assert resource.identifier == "test/test_module/test_provider"
            assert resource.base_domain == "spacelift.io"
            assert resource.start_line_number == 19
        elif resource.name == "test_provider":
            assert isinstance(resource, TerraformProvider)
            assert resource.current_version == ">1.0.0"
            assert resource.source == "test_provider/test_provider"
            assert resource.identifier == "test_provider/test_provider"
            assert resource.start_line_number == 4
            assert resource.base_domain is None
        elif resource.name == "test_provider2":
            assert isinstance(resource, TerraformProvider)
            assert resource.current_version == "1.0.5"
            assert resource.source == "spacelift.io/test_provider/test_provider2"
            assert resource.identifier == "test_provider/test_provider2"
            assert resource.start_line_number == 8
            assert resource.base_domain == "spacelift.io"
        else:
            raise Exception(f"Unknown resource '{resource.name}'.")


def test_invalid_terraform_code_parse_error(hcl_handler: HclHandler, invalid_terraform_code: str, tmp_path: Path):
    # Create a temporary Terraform file for testing
    tf_file = tmp_path.joinpath("test_file.tf")
    tf_file.write_text(invalid_terraform_code)
    with pytest.raises(HclParserException):
        hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=True)


def test_bump_resource_version(hcl_handler, valid_terraform_code: str, tmp_path: Path):
    # Create a TerraformModule resource for testing
    tf_file = tmp_path.joinpath("test_file.tf")
    tf_file.write_text(valid_terraform_code)
    resouces = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=True)

    # bump versions
    for resource in resouces:
        if resource.name == "test_module":
            resource.newest_version = "4.0.1"
        elif resource.name == "test_module2":
            resource.newest_version = "4.0.2"

        elif resource.name == "test_provider":
            resource.newest_version = "4.0.3"
        elif resource.name == "test_provider2":
            resource.newest_version = "4.0.4"
        hcl_handler.bump_resource_version(resource)

    resouces = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=True)
    # check if versions are bumped
    for resource in resouces:
        if resource.name == "test_module":
            assert resource.current_version == "4.0.1"
        elif resource.name == "test_module2":
            assert resource.current_version == "4.0.2"
        elif resource.name == "test_provider":
            assert resource.current_version == ">1.0.0"  # should not be bumped since it defines newer version
        elif resource.name == "test_provider2":
            assert resource.current_version == "4.0.4"


def test_get_all_terraform_files(hcl_handler):
    # Create a temporary directory with Terraform files for testing
    root_dir = Path("test_dir")
    root_dir.mkdir()
    tf_file1 = root_dir / "file1.tf"
    tf_file1.touch()
    tf_file2 = root_dir / "file2.tf"
    tf_file2.touch()

    # Test getting all Terraform files in the directory
    files = hcl_handler.get_all_terraform_files(root_dir)
    assert len(files) == 2
    assert tf_file1 in files
    assert tf_file2 in files

    # Clean up the temporary directory
    tf_file1.unlink()
    tf_file2.unlink()
    root_dir.rmdir()


def test_get_credentials_form_user_rc_file(hcl_handler, tmp_user_home: Path):
    # Create a temporary terraformrc file for testing

    # Create an instance of HclHandler with a mock HclEditCli
    with patch("pathlib.Path.home", return_value=tmp_user_home):
        # test without file
        credentials = hcl_handler.get_credentials_form_user_rc_file()
        assert len(credentials) == 0

        # Create a temporary terraformrc file for testing
        terraform_rc_file = tmp_user_home.joinpath(".terraformrc")
        terraform_rc_file.write_text(
            """
            credentials {
                test1 = {
                    token = "token1"
                }
                test2 = {
                    token = "token2"
                }
            }
        """
        )

        # Test getting credentials from the terraformrc file
        credentials = hcl_handler.get_credentials_form_user_rc_file()
        assert len(credentials) == 2
        assert credentials["test1"] == "token1"
        assert credentials["test2"] == "token2"

        # Clean up the temporary file
        terraform_rc_file.unlink()
