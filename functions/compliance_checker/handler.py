"""Lambda entry point: run the compliance checks and alert through SNS.

Triggered on a schedule by EventBridge. If one check cannot run (for example a
missing permission), the others still run and the failure is reported, so a
single problem never hides real findings.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Any

import boto3
from checks import (
    Finding,
    check_iam_users_without_mfa,
    check_open_security_groups,
    check_public_s3_buckets,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_FINDINGS_IN_MESSAGE = 50


def default_clients() -> dict[str, Any]:
    return {
        "s3": boto3.client("s3"),
        "ec2": boto3.client("ec2"),
        "iam": boto3.client("iam"),
        "sns": boto3.client("sns"),
    }


def run_checks(clients: dict[str, Any]) -> tuple[list[Finding], list[str]]:
    checks: list[tuple[str, Callable[[], list[Finding]]]] = [
        ("s3", lambda: check_public_s3_buckets(clients["s3"])),
        ("security-groups", lambda: check_open_security_groups(clients["ec2"])),
        ("iam-mfa", lambda: check_iam_users_without_mfa(clients["iam"])),
    ]

    findings: list[Finding] = []
    errors: list[str] = []
    for name, run in checks:
        try:
            findings.extend(run())
        except Exception as exc:
            logger.exception("Check %s failed", name)
            errors.append(f"{name}: {type(exc).__name__}")
    return findings, errors


def build_message(findings: list[Finding], errors: list[str]) -> str:
    lines = [f"{len(findings)} finding(s), {len(errors)} check(s) could not run.", ""]
    ordered = sorted(findings, key=lambda f: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[f.severity], f.resource))
    for finding in ordered[:MAX_FINDINGS_IN_MESSAGE]:
        lines.append(f"[{finding.severity}] {finding.check}: {finding.resource} - {finding.detail}")
    if len(ordered) > MAX_FINDINGS_IN_MESSAGE:
        lines.append(f"...and {len(ordered) - MAX_FINDINGS_IN_MESSAGE} more (see CloudWatch Logs).")
    for error in errors:
        lines.append(f"[ERROR] {error}")
    return "\n".join(lines)


def lambda_handler(event: Any, context: Any, clients: dict[str, Any] | None = None) -> dict[str, Any]:
    clients = clients or default_clients()
    findings, errors = run_checks(clients)

    summary = {
        "finding_count": len(findings),
        "high": sum(1 for f in findings if f.severity == "HIGH"),
        "errors": errors,
        "findings": [f.to_dict() for f in findings],
    }
    logger.info(json.dumps(summary))

    topic_arn = os.environ.get("SNS_TOPIC_ARN")
    if topic_arn and (findings or errors):
        clients["sns"].publish(
            TopicArn=topic_arn,
            Subject=f"Compliance check: {len(findings)} finding(s)"[:100],
            Message=build_message(findings, errors),
        )
    return summary
