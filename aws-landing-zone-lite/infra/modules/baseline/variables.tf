variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "alert_email" {
  description = "Email address for budget alerts."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD. Alerts at 80% actual and 100% forecast."
  type        = number
  default     = 10
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the plan role, as owner/name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must look like owner/name."
  }
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC provider. Set false if this account already has one (only one is allowed)."
  type        = bool
  default     = true
}

variable "force_destroy_logs" {
  description = "Let terraform destroy delete the log bucket even when it contains logs. Use true for demos only."
  type        = bool
  default     = false
}
