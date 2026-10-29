variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "alert_email" {
  description = "Email address that receives compliance findings. You must confirm the SNS subscription email."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge schedule for the checks."
  type        = string
  default     = "rate(1 day)"
}

variable "log_retention_days" {
  description = "How long to keep the Lambda's CloudWatch logs."
  type        = number
  default     = 365
}
