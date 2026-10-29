output "cloudtrail_arn" {
  description = "ARN of the account CloudTrail trail."
  value       = aws_cloudtrail.main.arn
}

output "log_bucket_name" {
  description = "Name of the CloudTrail log bucket."
  value       = aws_s3_bucket.logs.id
}

output "github_plan_role_arn" {
  description = "Role GitHub Actions can assume (read-only) via OIDC."
  value       = aws_iam_role.github_plan.arn
}
