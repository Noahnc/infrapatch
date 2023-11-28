from infrapatch.core.providers.terraform.base_terraform_provider import TerraformProvider


class TerraformProviderProvider(TerraformProvider):
    def get_provider_name(self) -> str:
        return "terraform_providers"

    def get_provider_display_name(self) -> str:
        return "Terraform Providers"
