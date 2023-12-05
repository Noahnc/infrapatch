from pathlib import Path
from unittest.mock import patch

import pytest

from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli, HclEditCliException


@pytest.fixture
def hcl_edit_cli():
    return HclEditCli()


def test_init_with_existing_binary_path(hcl_edit_cli):
    assert hcl_edit_cli._binary_path.exists()


def test_get_binary_path_windows():
    with patch("platform.system", return_value="Windows"):
        hcl_edit_cli = HclEditCli()
        assert hcl_edit_cli._get_binary_path().name == "hcledit_windows.exe"


def test_get_binary_path_linux():
    with patch("platform.system", return_value="Linux"):
        hcl_edit_cli = HclEditCli()
        assert hcl_edit_cli._get_binary_path().name == "hcledit_linux"


def test_get_binary_path_darwin():
    with patch("platform.system", return_value="Darwin"):
        hcl_edit_cli = HclEditCli()
        assert hcl_edit_cli._get_binary_path().name == "hcledit_darwin"


def test_get_binary_path_unsupported_platform():
    with patch("platform.system", return_value="Unsupported"):
        with pytest.raises(Exception):
            HclEditCli()


def test_update_hcl_value(hcl_edit_cli, tmp_path):
    file_path = tmp_path / "test_file.hcl"
    file_path.write_text('resource "test_resource" {\n  value = "old_value"\n}')

    hcl_edit_cli.update_hcl_value("resource.test_resource.value", file_path, "new_value")

    assert file_path.read_text() == 'resource "test_resource" {\n  value = "new_value"\n}'


def test_get_hcl_value(hcl_edit_cli, tmp_path):
    file_path = tmp_path / "test_file.hcl"
    file_path.write_text('resource "test_resource" {\n  value = "test_value"\n}')

    value = hcl_edit_cli.get_hcl_value("resource.test_resource.value", file_path)

    assert value == "test_value"


def test_get_hcl_value_non_existing_resource(hcl_edit_cli, tmp_path):
    file_path = tmp_path / "test_file.hcl"
    file_path.write_text('resource "test_resource" {\n  value = "test_value"\n}')

    with pytest.raises(HclEditCliException):
        hcl_edit_cli.get_hcl_value("non_existing_resource.value", file_path)


def test_run_hcl_edit_command_success(hcl_edit_cli):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "command_output"

        result = hcl_edit_cli._run_hcl_edit_command("get", "test_resource.value", Path("test_file.hcl"))

        assert result == "command_output"


def test_run_hcl_edit_command_failure(hcl_edit_cli):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "command_output"

        with pytest.raises(HclEditCliException):
            hcl_edit_cli._run_hcl_edit_command("get", "test_resource.value", Path("test_file.hcl"))
