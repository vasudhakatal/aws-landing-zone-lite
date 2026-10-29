import json

from checks import (
    check_iam_users_without_mfa,
    check_open_security_groups,
    check_public_s3_buckets,
)

ALL_BLOCKED = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


# --- S3 -------------------------------------------------------------------------------------


def test_bucket_without_public_access_block_is_flagged(s3):
    s3.create_bucket(Bucket="open-bucket")
    findings = check_public_s3_buckets(s3)
    assert [f.check for f in findings] == ["s3-public-access-block"]
    assert findings[0].resource == "s3://open-bucket"
    assert findings[0].severity == "MEDIUM"


def test_fully_blocked_bucket_is_clean(s3):
    s3.create_bucket(Bucket="locked-bucket")
    s3.put_public_access_block(
        Bucket="locked-bucket", PublicAccessBlockConfiguration=ALL_BLOCKED
    )
    assert check_public_s3_buckets(s3) == []


def test_partially_blocked_bucket_is_flagged(s3):
    s3.create_bucket(Bucket="half-bucket")
    config = {**ALL_BLOCKED, "BlockPublicPolicy": False}
    s3.put_public_access_block(Bucket="half-bucket", PublicAccessBlockConfiguration=config)
    assert [f.check for f in check_public_s3_buckets(s3)] == ["s3-public-access-block"]


def test_bucket_with_public_policy_is_high_severity(s3):
    s3.create_bucket(Bucket="public-policy")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::public-policy/*",
            }
        ],
    }
    s3.put_bucket_policy(Bucket="public-policy", Policy=json.dumps(policy))

    checks = {f.check: f for f in check_public_s3_buckets(s3)}
    assert checks["s3-public-policy"].severity == "HIGH"


def test_no_buckets_means_no_findings(s3):
    assert check_public_s3_buckets(s3) == []


# --- Security groups ------------------------------------------------------------------------


def _group(ec2, name):
    return ec2.create_security_group(GroupName=name, Description=name)["GroupId"]


def _allow(ec2, group_id, protocol, low, high, cidr="0.0.0.0/0"):
    ec2.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[
            {
                "IpProtocol": protocol,
                "FromPort": low,
                "ToPort": high,
                "IpRanges": [{"CidrIp": cidr}],
            }
        ],
    )


def test_ssh_open_to_the_world_is_flagged(ec2):
    group_id = _group(ec2, "ssh-open")
    _allow(ec2, group_id, "tcp", 22, 22)

    findings = check_open_security_groups(ec2)
    assert len(findings) == 1
    assert findings[0].severity == "HIGH"
    assert "tcp/22" in findings[0].detail
    assert group_id in findings[0].resource


def test_https_open_to_the_world_is_allowed(ec2):
    group_id = _group(ec2, "web")
    _allow(ec2, group_id, "tcp", 443, 443)
    _allow(ec2, group_id, "tcp", 80, 80)
    assert check_open_security_groups(ec2) == []


def test_port_range_that_includes_web_ports_is_still_flagged(ec2):
    group_id = _group(ec2, "wide-range")
    _allow(ec2, group_id, "tcp", 0, 65535)
    findings = check_open_security_groups(ec2)
    assert len(findings) == 1
    assert "tcp/0-65535" in findings[0].detail


def test_all_traffic_open_is_flagged(ec2):
    group_id = _group(ec2, "everything")
    ec2.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    )
    findings = check_open_security_groups(ec2)
    assert len(findings) == 1
    assert "all protocols and ports" in findings[0].detail


def test_private_cidr_is_not_flagged(ec2):
    group_id = _group(ec2, "internal")
    _allow(ec2, group_id, "tcp", 22, 22, cidr="10.0.0.0/8")
    assert check_open_security_groups(ec2) == []


def test_custom_allowed_ports_are_respected(ec2):
    group_id = _group(ec2, "custom")
    _allow(ec2, group_id, "tcp", 8443, 8443)
    assert check_open_security_groups(ec2, allowed_ports={8443}) == []
    assert len(check_open_security_groups(ec2)) == 1


# --- IAM ------------------------------------------------------------------------------------


def _enable_mfa(iam, user_name):
    serial = iam.create_virtual_mfa_device(VirtualMFADeviceName=f"{user_name}-device")[
        "VirtualMFADevice"
    ]["SerialNumber"]
    iam.enable_mfa_device(
        UserName=user_name,
        SerialNumber=serial,
        AuthenticationCode1="123456",
        AuthenticationCode2="654321",
    )


def test_console_user_without_mfa_is_flagged(iam):
    iam.create_user(UserName="alice")
    iam.create_login_profile(UserName="alice", Password="Sup3r-secret-pass!")

    findings = check_iam_users_without_mfa(iam)
    assert [f.resource for f in findings] == ["iam-user/alice"]
    assert findings[0].severity == "HIGH"


def test_console_user_with_mfa_is_clean(iam):
    iam.create_user(UserName="bob")
    iam.create_login_profile(UserName="bob", Password="Sup3r-secret-pass!")
    _enable_mfa(iam, "bob")
    assert check_iam_users_without_mfa(iam) == []


def test_user_without_console_access_is_not_flagged(iam):
    iam.create_user(UserName="ci-bot")
    assert check_iam_users_without_mfa(iam) == []
