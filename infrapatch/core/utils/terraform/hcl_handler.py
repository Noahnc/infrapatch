import glob
import logging as log
import platform
from pathlib import Path
from typing import Protocol, Sequence

import pygohcl

from infrapatch.core.models.versioned_terraform_resources import TerraformModule, TerraformProvider, VersionedTerraformResource
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli


class HclParserException(Exception):
    pass


class HclHandlerInterface(Protocol):
    def bump_resource_version(self, resource: VersionedTerraformResource):
        ...

    def get_terraform_resources_from_file(self, tf_file: Path, get_modules: bool = True, get_providers: bool = True) -> Sequence[VersionedTerraformResource]:
        ...

    def get_all_terraform_files(self, root: Path) -> Sequence[Path]:
        ...

    def get_credentials_form_user_rc_file(self) -> dict[str, str]:
        ...


class HclHandler(HclHandlerInterface):
    def __init__(self, hcl_edit_cli: HclEditCli):
        self.hcl_edit_cli = hcl_edit_cli
        pass

    def bump_resource_version(self, resource: VersionedTerraformResource):
        if not isinstance(resource, TerraformModule) and not isinstance(resource, TerraformProvider):
            raise Exception(f"Resource type '{type(resource)}' is not supported.")
        if resource.newest_version is None:
            raise Exception(f"Newest version of resource '{resource.name}' is not set.")
        if resource.installed_version_equal_or_newer_than_new_version():
            log.debug(f"Resource '{resource.name}' is already up to date.")
            return

        log.debug(f"Updating resource '{resource.resource_name}' with name '{resource.name}' from version '{resource.current_version}' to '{resource.newest_version}'.")
        if isinstance(resource, TerraformProvider):
            resource_name = f"terraform.required_providers.{resource.name}.version"
        elif isinstance(resource, TerraformModule):
            resource_name = f"module.{resource.name}.version"
        else:
            raise Exception(f"Resource type '{type(resource)}' is not supported.")

        self.hcl_edit_cli.update_hcl_value(resource_name, resource.source_file, resource.newest_version)

    def get_terraform_resources_from_file(self, tf_file: Path, get_modules: bool = True, get_providers: bool = True) -> Sequence[VersionedTerraformResource]:
        if get_modules is False and get_providers is False:
            raise Exception("At least one of the parameters 'modules' and 'providers' must be True.")

        if not tf_file.exists():
            raise Exception(f"File '{tf_file}' does not exist.")

        if not tf_file.is_file():
            raise Exception(f"Path '{tf_file}' is not a file.")

        with open(tf_file.absolute(), "r") as file:
            try:
                terraform_file_dict = pygohcl.loads(file.read())
            except Exception as e:
                raise HclParserException(f"Could not parse file '{tf_file}': {e}")
            found_resources = []
            if get_modules:
                found_resources.extend(self._get_terraform_modules_from_dict(terraform_file_dict, tf_file))
            if get_providers:
                found_resources.extend(self._get_terraform_providers_from_dict(terraform_file_dict, tf_file))
            return found_resources

    def _get_terraform_providers_from_dict(self, terraform_file_dict: dict, tf_file: Path) -> Sequence[TerraformProvider]:
        found_resources = []
        if "terraform" in terraform_file_dict:
            if "required_providers" in terraform_file_dict["terraform"]:
                providers = terraform_file_dict["terraform"]["required_providers"]
                for provider_name, provider_config in providers.items():
                    found_resources.append(
                        TerraformProvider(
                            name=provider_name, _source=provider_config["source"], current_version=provider_config["version"], _source_file=tf_file.absolute().as_posix()
                        )
                    )
        return found_resources

    def _get_terraform_modules_from_dict(self, terraform_file_dict: dict, tf_file: Path) -> Sequence[TerraformProvider]:
        found_resources = []
        if "module" in terraform_file_dict:
            modules = terraform_file_dict["module"]
            for module_name, value in modules.items():
                if "source" not in value:
                    log.debug(f"Skipping module '{module_name}' because it has no source attribute.")
                    continue
                found_resources.append(TerraformModule(name=module_name, _source=value["source"], current_version=value["version"], _source_file=tf_file.absolute().as_posix()))
        return found_resources

    def get_all_terraform_files(self, root: Path) -> Sequence[Path]:
        if not root.is_dir():
            raise Exception(f"Path '{root}' is not a directory.")
        search_string = "*.tf"
        if root is not None:
            search_string = f"{root}/**/*.tf"
        file_paths = glob.glob(search_string, recursive=True)
        files = [Path(file_path) for file_path in file_paths]
        return files

    def get_credentials_form_user_rc_file(self) -> dict[str, str]:
        # get the home of the user
        user_home = Path.home()

        credentials: dict[str, str] = {}

        # check if on windows
        if platform.system() == "Windows":
            terraform_rc_file = user_home.joinpath("AppData/Roaming/terraform.rc")
        else:
            terraform_rc_file = user_home.joinpath(".terraformrc")
        if not terraform_rc_file.exists() or not terraform_rc_file.is_file():
            log.debug("No terraformrc file found for the current user.")
            return credentials
        try:
            with open(terraform_rc_file.absolute(), "r") as file:
                try:
                    terraform_rc_file_dict = pygohcl.loads(file.read())
                except Exception as e:
                    log.error(f"Could not parse terraformrc file: {e}")
                    return credentials
                if "credentials" not in terraform_rc_file_dict:
                    log.debug("No credentials found in terraformrc file.")
                    return credentials
                for name, value in terraform_rc_file_dict["credentials"].items():
                    token = value["token"]
                    log.debug(f"Found the following credentials in terraformrc file: {name}={token[0:5]}...")
                    credentials[name] = value["token"]
                return credentials
        except Exception as e:
            log.error(f"Could not read terraformrc file: {e}")
            return credentials
