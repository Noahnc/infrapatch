import os
from pathlib import Path
from typing import Any
import logging as log


class MissingConfigException(Exception):
    pass


class ActionConfigProvider:
    github_token: str
    head_branch: str
    target_branch: str
    repository_name: str
    default_registry_domain: str
    working_directory: Path
    repository_root: Path
    report_only: bool
    registry_secrets: dict[str, str]

    def __init__(self) -> None:
        self.github_token = _get_value_from_env("GITHUB_TOKEN", secret=True)
        self.head_branch = _get_value_from_env("HEAD_BRANCH")
        self.target_branch = _get_value_from_env("TARGET_BRANCH")
        self.repository_name = _get_value_from_env("REPOSITORY_NAME")
        self.repository_root = Path(os.getcwd())
        self.working_directory = self.repository_root.joinpath(_get_value_from_env("WORKING_DIRECTORY_RELATIVE", default=""))
        self.default_registry_domain = _get_value_from_env("DEFAULT_REGISTRY_DOMAIN")
        self.registry_secrets = _get_credentials_from_string(_get_value_from_env("REGISTRY_SECRET_STRING", secret=True, default=""))
        self.report_only = _from_env_to_bool(_get_value_from_env("REPORT_ONLY", default="False").lower())


def _get_value_from_env(key: str, secret: bool = False, default: Any = None) -> Any:
    if key in os.environ:
        log_value = os.environ[key]
        if secret:
            log_value = f"{log_value[:3]}***"
        log.debug(f"Found the following value for {key}: {log_value}")
        return os.environ[key]
    if default is not None:
        log.debug(f"Using default value for {key}: {default}")
        return default
    raise MissingConfigException(f"Missing configuration for key: {key}")


def _get_credentials_from_string(credentials_string: str) -> dict[str, str]:
    credentials = {}
    if credentials_string == "":
        return credentials
    for line in credentials_string.splitlines():
        try:
            name, token = line.split("=", 1)
        except ValueError as e:
            log.debug(f"Secrets line '{line}' could not be split into name and token.")
            raise Exception(f"Error processing secrets: '{e}'")
        # add the name and token to the credentials dict
        credentials[name] = token
    return credentials


def _from_env_to_bool(value: str) -> bool:
    return value.lower() in ["true", "1", "yes", "y", "t"]
