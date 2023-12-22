from pathlib import Path
from unittest import mock

import pytest

import infrapatch.core.constants as cs
from infrapatch.core.models.versioned_terraform_resources import TerraformModule
from infrapatch.core.utils.options_processor import OptionsProcessor
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli
from infrapatch.core.utils.terraform.hcl_handler import HclHandler


@pytest.fixture
def options_processor():
    return OptionsProcessor()


@pytest.fixture
def tmp_user_home(tmp_path: Path):
    return tmp_path


@pytest.fixture
def hcl_handler():
    return HclHandler(hcl_edit_cli=HclEditCli())


@pytest.fixture
def terraform_code_with_options():
    return """
        terraform {
            required_providers {
                # infrapatch_options: ignore_resource=true
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
        # infrapatch_options: ignore_resource=true, test=test
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


def test_options_processing_from_file(options_processor: OptionsProcessor, hcl_handler: HclHandler, terraform_code_with_options: str, tmp_path: Path):
    # Create a temporary Terraform file for testing
    tf_file = tmp_path.joinpath("test_file.tf")
    tf_file.write_text(terraform_code_with_options)
    resouces = hcl_handler.get_terraform_resources_from_file(tf_file, get_modules=True, get_providers=True)

    # Check all resources parsed from the file for correct options
    for resource in resouces:
        resource = options_processor.process_options_for_resource(resource)
        if resource.name == "test_module":
            assert resource.options is None
        elif resource.name == "test_module2":
            assert resource.options is not None
            assert resource.options.ignore_resource is True
        elif resource.name == "test_provider":
            assert resource.options is not None
            assert resource.options.ignore_resource is True
        elif resource.name == "test_provider2":
            assert resource.options is None
        else:
            raise Exception(f"Unknown resource '{resource.name}'.")


def test_get_upper_line_with_non_valid_line_numbers(options_processor: OptionsProcessor):
    # Should return none since start line number is 1
    resource = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=1)
    upper_line_content = options_processor._get_upper_line_content(resource)
    assert upper_line_content is None

    # Should raise an exception since start line number is 0
    with pytest.raises(Exception):
        resource = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=0)
        upper_line_content = options_processor._get_upper_line_content(resource)


def test_get_upper_line_with_valid_line_numbers(options_processor: OptionsProcessor):
    resource1 = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=2)
    resource2 = TerraformModule(name="test_resource", current_version="1.0.0", _source_file="test_file.py", _source="test/test_module/test_provider", start_line_number=5)
    with mock.patch("builtins.open", mock.mock_open(read_data="line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n")):
        resource1_line = options_processor._get_upper_line_content(resource1)
        resource2_line = options_processor._get_upper_line_content(resource2)
    assert resource1_line == "line1"
    assert resource2_line == "line4"


options_strings = ["ignore_resource=true", "ignore_resource = true, test_option=2", "ignore_resource =false,test_option2=test4, test_option3 = test5"]


@pytest.mark.parametrize("options_string", options_strings)
def test_options_format_processing(options_processor: OptionsProcessor, options_string: str):
    options_dict = options_processor._process_options_string(options_string)
    assert options_dict is not None
    assert options_dict is not {}

    if options_string == "ignore_resource=true":
        assert options_dict["ignore_resource"] == "true"
    elif options_string == "ignore_resource = true, test_option=2":
        assert options_dict["ignore_resource"] == "true"
        assert options_dict["test_option"] == "2"
    elif options_string == "ignore_resource =false,test_option2=test4, test_option3 = test5":
        assert options_dict["ignore_resource"] == "false"
        assert options_dict["test_option2"] == "test4"
        assert options_dict["test_option3"] == "test5"
    else:
        raise Exception(f"Unknown options string '{options_string}'.")


@pytest.mark.parametrize("options_string", options_strings)
def test_get_options_object(options_processor: OptionsProcessor, options_string: str):
    options = options_processor._get_options_object(f"{cs.infrapatch_options_prefix} {options_string}")
    assert options is not None

    if options_string == "ignore_resource=true":
        assert options.ignore_resource is True
    elif options_string == "ignore_resource =false,test_option2=test4, test_option3 = test5":
        assert options.ignore_resource is False
        with pytest.raises(AttributeError):
            options.test_option2  # type: ignore
