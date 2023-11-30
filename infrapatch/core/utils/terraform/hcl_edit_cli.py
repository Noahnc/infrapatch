import logging as log
import platform
import subprocess
from pathlib import Path
from typing import Optional, Protocol, Union


class HclEditCliException(Exception):
    pass


class HclEditCliInterface(Protocol):
    def update_hcl_value(self, resource: str, file: Path, value: str):
        ...

    def get_hcl_value(self, resource: str, file: Path) -> str:
        ...


class HclEditCli(HclEditCliInterface):
    def __init__(self):
        self._binary_path = self._get_binary_path()
        if not self._binary_path.exists() and not self._binary_path.is_file():
            raise Exception(f"Binary '{self._binary_path.absolute().as_posix()}' does not exist.")

    def _get_binary_path(self) -> Path:
        current_folder = Path(__file__).parent
        binary_folder = current_folder.joinpath("bin")
        if platform.system() == "Windows":
            return binary_folder.joinpath("hcledit_windows.exe")
        elif platform.system() == "Linux":
            return binary_folder.joinpath("hcledit_linux")
        elif platform.system() == "Darwin":
            return binary_folder.joinpath("hcledit_darwin")
        else:
            raise Exception(f"Unsupported platform: {platform.system()}, supported platforms are: Windows, Linux, Darwin.")

    def update_hcl_value(self, resource: str, file: Path, value: str):
        self._run_hcl_edit_command("update", resource, file, value)

    def get_hcl_value(self, resource: str, file: Path) -> str:
        result = self._run_hcl_edit_command("get", resource, file)
        if result is None:
            raise HclEditCliException(f"Could not get value for resource '{resource}' from file '{file}'.")
        return result

    def _run_hcl_edit_command(self, action: str, resource: str, file: Path, value: Union[str, None] = None) -> Optional[str]:
        command = [self._binary_path.absolute().as_posix(), action, resource]
        if value is not None:
            command.append(value)
        command.append(file.absolute().as_posix())
        command_string = " ".join(command)
        log.debug(f"Executing command: {command_string}")
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except Exception as e:
            raise HclEditCliException(f"Could not execute CLI command '{command_string}': {e}")
        if result.returncode != 0:
            log.error(f"Stdout: {result.stdout}")
            raise HclEditCliException(f"CLI command '{command_string}' failed with exit code {result.returncode}.")
        return result.stdout
