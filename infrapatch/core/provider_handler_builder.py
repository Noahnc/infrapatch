import logging as log
from pathlib import Path
from typing import Self
from infrapatch.core.providers.terraform.terraform_provider_provider import TerraformProviderProvider

from infrapatch.core.providers.terraform.terraform_module_provider import TerraformModuleProvider
from git import Repo
from rich.console import Console

import infrapatch.core.constants as const
import infrapatch.core.constants as cs
from infrapatch.core.provider_handler import ProviderHandler
from infrapatch.core.utils.terraform.hcl_edit_cli import HclEditCli
from infrapatch.core.utils.terraform.hcl_handler import HclHandler
from infrapatch.core.utils.terraform.registry_handler import RegistryHandler


class ProviderHandlerBuilder:
    def __init__(self, working_directory: Path) -> None:
        self.providers = []
        self.working_directory = working_directory
        self.registry_handler = None
        self.git_integration = False
        pass

    def add_terraform_registry_configuration(self, default_registry_domain: str, credentials: dict[str, str]) -> Self:
        log.debug(f"Using {default_registry_domain} as default registry domain for Terraform.")
        log.debug(f"Found {len(credentials)} credentials for Terraform registries.")
        self.registry_handler = RegistryHandler(default_registry_domain, credentials)
        return self

    def with_terraform_module_provider(self) -> Self:
        if self.registry_handler is None:
            raise Exception("No registry configuration added to ProviderHandlerBuilder.")
        log.debug("Adding TerraformModuleProvider to ProviderHandlerBuilder.")
        tf_module_provider = TerraformModuleProvider(HclEditCli(), self.registry_handler, HclHandler(HclEditCli()), self.working_directory)
        self.providers.append(tf_module_provider)
        return self

    def with_terraform_provider_provider(self) -> Self:
        if self.registry_handler is None:
            raise Exception("No registry configuration added to ProviderHandlerBuilder.")
        log.debug("Adding TerraformModuleProvider to ProviderHandlerBuilder.")
        tf_module_provider = TerraformProviderProvider(HclEditCli(), self.registry_handler, HclHandler(HclEditCli()), self.working_directory)
        self.providers.append(tf_module_provider)
        return self

    def with_git_integration(self) -> Self:
        log.debug("Enabling Git integration.")
        self.git_integration = True
        return self

    def build(self) -> ProviderHandler:
        if len(self.providers) == 0:
            raise Exception("No providers added to ProviderHandlerBuilder.")
        statistics_file = self.working_directory.joinpath(f"{cs.APP_NAME}_Statistics.json")
        git_repo = None
        if self.git_integration:
            git_repo = Repo(self.working_directory)
        return ProviderHandler(providers=self.providers, console=Console(width=const.CLI_WIDTH), statistics_file=statistics_file, repo=git_repo)
