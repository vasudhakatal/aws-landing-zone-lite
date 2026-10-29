output "function_name" {
  description = "Name of the compliance checker Lambda."
  value       = aws_lambda_function.checker.function_name
}

output "sns_topic_arn" {
  description = "SNS topic that receives findings."
  value       = aws_sns_topic.alerts.arn
}
