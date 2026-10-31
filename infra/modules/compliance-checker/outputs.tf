output "function_name" {
  description = "Name of the compliance checker Lambda."
  value       = aws_lambda_function.checker.function_name
}

output "sns_topic_arn" {
  description = "SNS topic that receives findings."
  value       = aws_sns_topic.alerts.arn
}

output "ops_sns_topic_arn" {
  description = "SNS topic that receives the checker's own error alarm."
  value       = aws_sns_topic.ops.arn
}

output "dashboard_name" {
  description = "CloudWatch dashboard showing invocations, errors and duration."
  value       = aws_cloudwatch_dashboard.checker.dashboard_name
}
