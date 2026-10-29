from unittest.mock import MagicMock

import boto3
import handler

TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:alerts"


def make_clients(sns=None):
    return {
        "s3": boto3.client("s3"),
        "ec2": boto3.client("ec2"),
        "iam": boto3.client("iam"),
        "sns": sns or MagicMock(),
    }


def test_clean_account_publishes_nothing(aws, monkeypatch):
    monkeypatch.setenv("SNS_TOPIC_ARN", TOPIC_ARN)
    clients = make_clients()

    summary = handler.lambda_handler({}, None, clients=clients)

    assert summary["finding_count"] == 0
    assert summary["errors"] == []
    clients["sns"].publish.assert_not_called()


def test_findings_are_summarised_and_published(aws, monkeypatch):
    monkeypatch.setenv("SNS_TOPIC_ARN", TOPIC_ARN)
    boto3.client("s3").create_bucket(Bucket="open-bucket")
    clients = make_clients()

    summary = handler.lambda_handler({}, None, clients=clients)

    assert summary["finding_count"] == 1
    clients["sns"].publish.assert_called_once()
    call = clients["sns"].publish.call_args.kwargs
    assert call["TopicArn"] == TOPIC_ARN
    assert "1 finding(s)" in call["Subject"]
    assert "s3://open-bucket" in call["Message"]


def test_without_a_topic_it_still_returns_a_summary(aws):
    boto3.client("s3").create_bucket(Bucket="open-bucket")
    clients = make_clients()

    summary = handler.lambda_handler({}, None, clients=clients)

    assert summary["finding_count"] == 1
    clients["sns"].publish.assert_not_called()


def test_one_failing_check_does_not_hide_the_others(aws, monkeypatch):
    monkeypatch.setenv("SNS_TOPIC_ARN", TOPIC_ARN)
    boto3.client("s3").create_bucket(Bucket="open-bucket")
    clients = make_clients()
    clients["ec2"] = MagicMock()
    clients["ec2"].get_paginator.side_effect = RuntimeError("access denied")

    summary = handler.lambda_handler({}, None, clients=clients)

    assert summary["finding_count"] == 1  # the S3 finding is still reported
    assert summary["errors"] == ["security-groups: RuntimeError"]
    message = clients["sns"].publish.call_args.kwargs["Message"]
    assert "[ERROR] security-groups" in message


def test_message_puts_high_severity_first(aws):
    findings = [
        handler.Finding("a", "r1", "LOW", "low one"),
        handler.Finding("b", "r2", "HIGH", "high one"),
        handler.Finding("c", "r3", "MEDIUM", "medium one"),
    ]
    lines = handler.build_message(findings, []).splitlines()
    assert lines[2].startswith("[HIGH]")
    assert lines[3].startswith("[MEDIUM]")
    assert lines[4].startswith("[LOW]")


def test_long_messages_are_truncated(aws):
    findings = [handler.Finding("x", f"r{i}", "LOW", "d") for i in range(60)]
    message = handler.build_message(findings, [])
    assert "...and 10 more" in message
