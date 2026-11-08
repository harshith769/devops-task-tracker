terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # State is kept locally in terraform.tfstate for this lab.
  # For a team, move it to a remote backend - see backend.tf.example.
}
