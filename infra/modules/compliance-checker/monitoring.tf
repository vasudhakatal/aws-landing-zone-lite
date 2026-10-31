# ------------------------------------------------------------------------------------------
# Monitoring: an alarm when the checker itself fails, and a small dashboard.
#
# Findings go to the compliance topic (see main.tf). This alarm covers a different problem: the
# checker crashing or not running, which would otherwise look like "no findings".
#
# CloudWatch alarms cannot publish to an SNS topic encrypted with the AWS-managed key
# (alias/aws/sns), so the operations topic uses its own customer-managed key whose policy lets
# CloudWatch use it.
# ------------------------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ops_key" {
  statement {
    sid       = "AccountAdministration"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  statement {
    sid       = "AllowCloudWatchAlarmsToPublish"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey*"]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
  }
}

resource "aws_kms_key" "ops" {
  description             = "${local.function_name} operations alert topic"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  policy                  = data.aws_iam_policy_document.ops_key.json
}

resource "aws_sns_topic" "ops" {
  name              = "${var.name_prefix}-checker-ops-alerts"
  kms_master_key_id = aws_kms_key.ops.arn
}

resource "aws_sns_topic_subscription" "ops_email" {
  topic_arn = aws_sns_topic.ops.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "checker_errors" {
  alarm_name          = "${local.function_name}-errors"
  alarm_description   = "The compliance checker Lambda raised an error. Check its CloudWatch logs."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.checker.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
}

resource "aws_cloudwatch_dashboard" "checker" {
  dashboard_name = local.function_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Invocations and errors"
          region = data.aws_region.current.name
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.checker.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.checker.function_name],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Duration (ms)"
          region = data.aws_region.current.name
          stat   = "Maximum"
          period = 300
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.checker.function_name],
          ]
        }
      },
    ]
  })
}

data "aws_region" "current" {}
