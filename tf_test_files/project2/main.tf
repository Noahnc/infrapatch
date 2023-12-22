
module "test_module" {
  source  = "hashicorp/consul/aws"
  version = "0.2.0"
}

# This resource should be ignored by infrapatch
# infrapatch_options: ignore_resource=true
module "test_module6" {
  source  = "hashicorp/consul/aws"
  version = "0.2.0"
}