from pathlib import Path
import subprocess
from typing import Union
import logging as log


class GitException(Exception):
    pass


class Git:
    _repo_path: Path

    def __init__(self, repo_path: Path):
        self._repo_path = repo_path

    def run_git_command(self, command: list[str]) -> tuple[str, Union[str, None]]:
        command = ["git", *command]
        command_string = " ".join(command)
        log.debug(f"Executing git command: {command_string}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=self._repo_path.absolute().as_posix())
        except Exception as e:
            raise GitException(f"Error executing git command {command_string} with error: {e}")
        if result.returncode != 0:
            raise GitException(f"Git command {command_string} exited with non-zero exit code {result.returncode}: {result.stderr}")
        return result.stdout, result.stderr

    def fetch_origin(self):
        log.debug("Fetching origin")
        self.run_git_command(["fetch", "origin"])

    def checkout_branch(self, target: str, origin: str):
        log.debug(f"Checking out branch {target} from {origin}")
        self.run_git_command(["checkout", "-b", target, origin])

    def push(self, additional_arguments: list[str] = []):
        self.run_git_command(["push", *additional_arguments])
