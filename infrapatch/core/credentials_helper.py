from typing import Union
import json
import logging as log
import infrapatch.core.constants as cs
from pathlib import Path

from infrapatch.core.utils.terraform.hcl_handler import HclHandler


def get_registry_credentials(hcl_handler: HclHandler, credentials_file: Union[Path, None] = None) -> dict[str, str]:
    credentials = hcl_handler.get_credentials_form_user_rc_file()
    if credentials_file is None:
        credentials_file = Path.cwd().joinpath(cs.DEFAULT_CREDENTIALS_FILE_NAME)
    else:
        credentials_file = Path(credentials_file)
    if not credentials_file.exists() or not credentials_file.is_file():
        log.debug(f"No credentials file found at '{credentials_file}'.")
        return credentials
    try:
        with open(credentials_file.absolute(), "r") as file:
            credentials_file_dict = json.load(file)
            for name, token in credentials_file_dict.items():
                log.debug(f"Found the following credentials in credentials file: {name}={token[0:5]}...")
                if name in credentials:
                    log.debug(f"Credentials for registry '{name}' already found in terraformrc file and credentials file, using value from credentials file.")
                credentials[name] = token
        return credentials
    except Exception as e:
        raise Exception(f"Could not read credentials file: {e}")
