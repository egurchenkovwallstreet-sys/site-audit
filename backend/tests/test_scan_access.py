import pytest
from fastapi import HTTPException

from app.services.scan_access import new_public_token, validate_public_token


def test_new_public_token_length():
    t = new_public_token()
    assert len(t) >= 16
    assert validate_public_token(t) == t


def test_validate_rejects_numeric_guess():
    with pytest.raises(HTTPException) as exc:
        validate_public_token("310")
    assert exc.value.status_code == 404


def test_validate_rejects_weird():
    for bad in ("", "!!!", "a" * 200):
        with pytest.raises(HTTPException):
            validate_public_token(bad)