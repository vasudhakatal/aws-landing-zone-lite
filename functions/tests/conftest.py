import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def fake_aws_environment(monkeypatch):
    """Make sure tests can never touch a real AWS account."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)


@pytest.fixture
def aws():
    with mock_aws():
        yield


@pytest.fixture
def s3(aws):
    return boto3.client("s3")


@pytest.fixture
def ec2(aws):
    return boto3.client("ec2")


@pytest.fixture
def iam(aws):
    return boto3.client("iam")
