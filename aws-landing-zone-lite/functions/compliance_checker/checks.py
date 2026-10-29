"""Account compliance checks.

Each check takes a boto3 client and returns a list of Findings. Checks only read
configuration; nothing here changes the account.

Known limits (also listed in the README):
- IAM users with access keys but no console password are not flagged for MFA.
- Only the account's own S3 buckets and security groups in the Lambda's region
  are inspected for security groups.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from botocore.exceptions import ClientError

Severity = Literal["HIGH", "MEDIUM", "LOW"]

# Ports that are normally fine to expose to the whole internet (web traffic).
DEFAULT_ALLOWED_PUBLIC_PORTS: frozenset[int] = frozenset({80, 443})

_PUBLIC_ACCESS_BLOCK_KEYS = (
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",
)


@dataclass(frozen=True)
class Finding:
    check: str
    resource: str
    severity: Severity
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


# --- S3 -------------------------------------------------------------------------------------


def check_public_s3_buckets(s3: Any) -> list[Finding]:
    """Flag buckets without full Block Public Access, and buckets with a public policy."""
    findings: list[Finding] = []
    for bucket in s3.list_buckets().get("Buckets", []):
        findings.extend(_check_bucket(s3, bucket["Name"]))
    return findings


def _check_bucket(s3: Any, name: str) -> list[Finding]:
    resource = f"s3://{name}"
    findings: list[Finding] = []

    try:
        config = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
        fully_blocked = all(config.get(key, False) for key in _PUBLIC_ACCESS_BLOCK_KEYS)
    except ClientError as exc:
        if _error_code(exc) != "NoSuchPublicAccessBlockConfiguration":
            return [
                Finding("s3-inspection-error", resource, "LOW", f"Could not inspect: {_error_code(exc)}")
            ]
        fully_blocked = False

    if not fully_blocked:
        findings.append(
            Finding(
                "s3-public-access-block",
                resource,
                "MEDIUM",
                "Block Public Access is not fully enabled on this bucket",
            )
        )

    try:
        status = s3.get_bucket_policy_status(Bucket=name)["PolicyStatus"]
        if status.get("IsPublic"):
            findings.append(
                Finding("s3-public-policy", resource, "HIGH", "Bucket policy allows public access")
            )
    except ClientError as exc:
        if _error_code(exc) != "NoSuchBucketPolicy":
            findings.append(
                Finding("s3-inspection-error", resource, "LOW", f"Could not inspect: {_error_code(exc)}")
            )

    return findings


# --- Security groups ------------------------------------------------------------------------


def _open_to_world(permission: dict[str, Any]) -> bool:
    return any(r.get("CidrIp") == "0.0.0.0/0" for r in permission.get("IpRanges", [])) or any(
        r.get("CidrIpv6") == "::/0" for r in permission.get("Ipv6Ranges", [])
    )


def check_open_security_groups(
    ec2: Any, allowed_ports: Iterable[int] = DEFAULT_ALLOWED_PUBLIC_PORTS
) -> list[Finding]:
    """Flag inbound rules open to 0.0.0.0/0 or ::/0, except single allowed ports (80, 443)."""
    allowed = set(allowed_ports)
    findings: list[Finding] = []

    for page in ec2.get_paginator("describe_security_groups").paginate():
        for group in page["SecurityGroups"]:
            for permission in group.get("IpPermissions", []):
                if not _open_to_world(permission):
                    continue

                protocol = permission.get("IpProtocol")
                if protocol in ("icmp", "icmpv6"):
                    continue

                if protocol == "-1":
                    what = "all protocols and ports"
                else:
                    low, high = permission["FromPort"], permission["ToPort"]
                    if low == high and low in allowed:
                        continue
                    ports = str(low) if low == high else f"{low}-{high}"
                    what = f"{protocol}/{ports}"

                findings.append(
                    Finding(
                        "security-group-open-to-internet",
                        f"{group['GroupId']} ({group.get('GroupName', '')})",
                        "HIGH",
                        f"Inbound {what} is open to the internet",
                    )
                )
    return findings


# --- IAM ------------------------------------------------------------------------------------


def _has_console_password(iam: Any, user_name: str) -> bool:
    try:
        iam.get_login_profile(UserName=user_name)
        return True
    except ClientError as exc:
        if _error_code(exc) == "NoSuchEntity":
            return False
        raise


def check_iam_users_without_mfa(iam: Any) -> list[Finding]:
    """Flag IAM users who can sign in to the console but have no MFA device."""
    findings: list[Finding] = []
    for page in iam.get_paginator("list_users").paginate():
        for user in page["Users"]:
            name = user["UserName"]
            if not _has_console_password(iam, name):
                continue
            if not iam.list_mfa_devices(UserName=name)["MFADevices"]:
                findings.append(
                    Finding(
                        "iam-user-without-mfa",
                        f"iam-user/{name}",
                        "HIGH",
                        "User has console access but no MFA device",
                    )
                )
    return findings
