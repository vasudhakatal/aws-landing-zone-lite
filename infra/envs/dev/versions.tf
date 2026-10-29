terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # State is stored locally by default. For anything beyond a personal demo, use a remote
  # backend (S3 with locking). See infra/README.md.
}
