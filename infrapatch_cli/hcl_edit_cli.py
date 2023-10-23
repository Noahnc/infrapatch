import logging as log
import platform
import subprocess
from pathlib import Path
from typing import Optional


class HclEditCli:
    def __init__(self):
        pass

    def _get_binary_path(self) -> Path:
        binary_folder = Path(__file__).parent.joinpath("bin")
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
            raise Exception(f"Could not get value for resource '{resource}' from file '{file}'.")

    def _run_hcl_edit_command(self, action: str, resource: str, file: Path, value: str = None) -> Optional[str]:
        command = [self._get_binary_path().absolute().as_posix(), action, resource]
        if value is not None:
            command.append(value)
        command.append(file.absolute().as_posix())
        command_string = " ".join(command)
        log.debug(f"Executing command: {command_string}")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(f"Stdout: {result.stdout}")
            raise Exception(
                f"CLI command '{command_string}' failed with exit code {result.returncode}.")
        return result.stdout
