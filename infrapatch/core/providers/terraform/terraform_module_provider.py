from infrapatch.core.providers.terraform.base_terraform_provider import TerraformProvider


class TerraformModuleProvider(TerraformProvider):
    def get_provider_name(self) -> str:
        return "terraform_modules"

    def get_provider_display_name(self) -> str:
        return "Terraform Modules"
