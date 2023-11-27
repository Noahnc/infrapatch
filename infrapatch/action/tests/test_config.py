import os
from pathlib import Path

import pytest

from infrapatch.action.config import ActionConfigProvider, MissingConfigException, _from_env_to_bool, _get_credentials_from_string, _get_value_from_env


def test_get_credentials_from_string():
    # Test case 1: Empty credentials string
    credentials_string = ""
    expected_result = {}
    assert _get_credentials_from_string(credentials_string) == expected_result

    # Test case 2: Single line credentials string
    credentials_string = "username=abc123"
    expected_result = {"username": "abc123"}
    assert _get_credentials_from_string(credentials_string) == expected_result

    # Test case 3: Multiple line credentials string
    credentials_string = "username=abc123\npassword=xyz789\ntoken=123456"
    expected_result = {"username": "abc123", "password": "xyz789", "token": "123456"}
    assert _get_credentials_from_string(credentials_string) == expected_result

    # Test case 4: Invalid credentials string
    credentials_string = "username=abc123\npassword"
    try:
        _get_credentials_from_string(credentials_string)
    except Exception as e:
        assert str(e) == "Error processing secrets: 'not enough values to unpack (expected 2, got 1)'"


def test_get_value_from_env():
    # Test case 1: Value exists in os.environ
    os.environ["TEST_VALUE"] = "abc123"
    assert _get_value_from_env("TEST_VALUE") == "abc123"

    # Test case 2: Value does not exist in os.environ
    os.environ.clear()
    try:
        _get_value_from_env("TEST_VALUE")
    except MissingConfigException as e:
        assert str(e) == "Missing configuration for key: TEST_VALUE"

    # Test case 3: Value does not exist in os.environ, but default is provided
    assert _get_value_from_env("TEST_VALUE", default="abc123") == "abc123"


@pytest.mark.parametrize("working_directory_relative_path", ["/working/directory", ""], ids=lambda d: f"x={d}")
def test_action_config_init(working_directory_relative_path):
    # Test case 1: All values exist in os.environ
    os.environ["GITHUB_TOKEN"] = "abc123"
    os.environ["HEAD_BRANCH"] = "main"
    os.environ["TARGET_BRANCH"] = "develop"
    os.environ["REPOSITORY_NAME"] = "my-repo"
    os.environ["WORKING_DIRECTORY_RELATIVE"] = working_directory_relative_path
    os.environ["DEFAULT_REGISTRY_DOMAIN"] = "registry.example.com"
    os.environ["REGISTRY_SECRET_STRING"] = "test_registry.ch=abc123"
    os.environ["REPORT_ONLY"] = "False"

    config = ActionConfigProvider()

    assert config.github_token == "abc123"
    assert config.head_branch == "main"
    assert config.target_branch == "develop"
    assert config.repository_name == "my-repo"
    assert config.working_directory == Path(os.getcwd()).joinpath(working_directory_relative_path)
    assert config.repository_root == Path(os.getcwd())
    assert config.default_registry_domain == "registry.example.com"
    assert config.registry_secrets == {"test_registry.ch": "abc123"}
    assert config.report_only is False

    # Test case 2: Missing values in os.environ
    os.environ.clear()
    try:
        config = ActionConfigProvider()
    except MissingConfigException as e:
        assert str(e).__contains__("Missing configuration for key")


def test_env_to_bool():
    # Test case 1: True values
    assert _from_env_to_bool("true") is True
    assert _from_env_to_bool("1") is True
    assert _from_env_to_bool("yes") is True
    assert _from_env_to_bool("y") is True
    assert _from_env_to_bool("t") is True

    # Test case 2: False values
    assert _from_env_to_bool("false") is False
    assert _from_env_to_bool("0") is False
    assert _from_env_to_bool("no") is False
    assert _from_env_to_bool("n") is False
    assert _from_env_to_bool("f") is False

    # Test case 3: Case-insensitive
    assert _from_env_to_bool("True") is True
    assert _from_env_to_bool("FALSE") is False
    assert _from_env_to_bool("YeS") is True
    assert _from_env_to_bool("N") is False
    assert _from_env_to_bool("T") is True
