

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "0.0.1"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~>1.1.0"
    }
  }
}