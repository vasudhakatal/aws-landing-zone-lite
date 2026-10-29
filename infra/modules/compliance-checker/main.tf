locals {
  function_name = "${var.name_prefix}-compliance-checker"
}

# Package the function code (checks.py + handler.py) into a zip.
data "archive_file" "checker" {
  type        = "zip"
  source_dir  = "${path.module}/../../../functions/compliance_checker"
  output_path = "${path.module}/.build/compliance_checker.zip"
  excludes    = ["__pycache__"]
}

# ------------------------------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------------------------------

resource "aws_sns_topic" "alerts" {
  name              = "${var.name_prefix}-compliance-alerts"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ------------------------------------------------------------------------------------------
# Least-privilege role: read-only inspection calls, publish to one topic, write own logs
# ------------------------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "checker" {
  name               = "${local.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_cloudwatch_log_group" "checker" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "checker" {
  # These list/describe/get calls do not support resource-level restrictions.
  statement {
    sid = "ReadOnlyInspection"
    actions = [
      "s3:ListAllMyBuckets",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketPolicyStatus",
      "ec2:DescribeSecurityGroups",
      "iam:ListUsers",
      "iam:GetLoginProfile",
      "iam:ListMFADevices",
    ]
    resources = ["*"]
  }

  # X-Ray segment uploads do not support resource-level restrictions either.
  statement {
    sid       = "XRayTracing"
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
    resources = ["*"]
  }

  statement {
    sid       = "PublishAlerts"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }

  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.checker.arn}:*"]
  }
}

resource "aws_iam_role_policy" "checker" {
  name   = "${local.function_name}-policy"
  role   = aws_iam_role.checker.id
  policy = data.aws_iam_policy_document.checker.json
}

# ------------------------------------------------------------------------------------------
# Function and schedule
# ------------------------------------------------------------------------------------------

resource "aws_lambda_function" "checker" {
  function_name    = local.function_name
  role             = aws_iam_role.checker.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.checker.output_path
  source_code_hash = data.archive_file.checker.output_base64sha256
  timeout          = 60
  memory_size      = 128

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.checker, aws_iam_role_policy.checker]
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${local.function_name}-schedule"
  description         = "Runs the compliance checker on a schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "checker" {
  rule = aws_cloudwatch_event_rule.schedule.name
  arn  = aws_lambda_function.checker.arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
