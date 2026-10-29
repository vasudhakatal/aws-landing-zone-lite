output "cloudtrail_arn" {
  value = module.baseline.cloudtrail_arn
}

output "log_bucket_name" {
  value = module.baseline.log_bucket_name
}

output "github_plan_role_arn" {
  value = module.baseline.github_plan_role_arn
}

output "compliance_checker_function" {
  value = module.compliance_checker.function_name
}

output "alerts_topic_arn" {
  value = module.compliance_checker.sns_topic_arn
}
