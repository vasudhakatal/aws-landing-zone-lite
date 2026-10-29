variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "ap-southeast-2"
}

variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
  default     = "lzlite-dev"
}

variable "alert_email" {
  description = "Email for budget alerts and compliance findings."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository (owner/name) allowed to assume the read-only plan role."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD."
  type        = number
  default     = 10
}

variable "create_github_oidc_provider" {
  description = "Set false if the account already has a GitHub OIDC provider."
  type        = bool
  default     = true
}

variable "force_destroy_logs" {
  description = "Allow terraform destroy to delete the CloudTrail log bucket with its contents. Demos only."
  type        = bool
  default     = false
}

variable "create_network" {
  description = "Create the example VPC. Off by default; the VPC itself is free but flow logs cost a little."
  type        = bool
  default     = false
}
