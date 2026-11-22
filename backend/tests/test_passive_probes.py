from app.scan.passive_probes import _body_matches


def test_git_head_signature() -> None:
    assert _body_matches("ref: refs/heads/main\n", (r"ref:\s+refs/",))


def test_env_signature() -> None:
    assert _body_matches("DB_PASSWORD=secret\nAPP_ENV=prod\n", (r"^[a-z0-9_]+=",))