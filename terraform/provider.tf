# The AWS provider is pointed at a local AWS emulator (Moto server or
# LocalStack) listening on var.aws_endpoint, so nothing is created in a real
# AWS account and no cost is incurred. The dummy credentials are accepted by
# the emulator; never commit real keys.
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    ec2 = var.aws_endpoint
    iam = var.aws_endpoint
    s3  = var.aws_endpoint
    sts = var.aws_endpoint
  }

  default_tags {
    tags = local.common_tags
  }
}
