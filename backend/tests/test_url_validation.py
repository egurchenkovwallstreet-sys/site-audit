import pytest

from app.compliance.url_validation import validate_target_url


def test_validate_accepts_public_https():
    assert validate_target_url("https://example.com/").startswith("https://")


def test_validate_rejects_private_ip():
    with pytest.raises(ValueError):
        validate_target_url("http://192.168.1.1/")


def test_validate_rejects_localhost():
    with pytest.raises(ValueError):
        validate_target_url("http://localhost/")


def test_validate_rejects_file_scheme():
    with pytest.raises(ValueError):
        validate_target_url("file:///etc/passwd")