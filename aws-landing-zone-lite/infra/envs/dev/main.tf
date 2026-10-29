provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-landing-zone-lite"
      env        = "dev"
      managed_by = "terraform"
    }
  }
}

module "baseline" {
  source = "../../modules/baseline"

  name_prefix                 = var.name_prefix
  alert_email                 = var.alert_email
  monthly_budget_usd          = var.monthly_budget_usd
  github_repository           = var.github_repository
  create_github_oidc_provider = var.create_github_oidc_provider
  force_destroy_logs          = var.force_destroy_logs
}

module "compliance_checker" {
  source = "../../modules/compliance-checker"

  name_prefix = var.name_prefix
  alert_email = var.alert_email
}

module "network" {
  source = "../../modules/network"
  count  = var.create_network ? 1 : 0

  name_prefix = var.name_prefix
}
