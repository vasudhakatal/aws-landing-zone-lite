variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "cidr_block" {
  description = "CIDR range for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread subnets across."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3."
  }
}

variable "flow_log_retention_days" {
  description = "How long to keep VPC flow logs."
  type        = number
  default     = 365
}
