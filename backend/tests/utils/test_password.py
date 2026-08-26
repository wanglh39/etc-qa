from utils.password import check_password_policy, hash_password, needs_rehash, verify_password


class TestPassword:
    def test_hash_and_verify_roundtrip(self):
        h = hash_password("my-secret-password")
        assert h.startswith("pbkdf2_sha256$260000$")
        assert verify_password("my-secret-password", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_verify_legacy_plaintext(self):
        assert verify_password("123456", "123456") is True
        assert verify_password("wrong", "123456") is False

    def test_needs_rehash(self):
        assert needs_rehash("123456") is True
        assert needs_rehash(hash_password("x")) is False

    def test_hash_is_salted(self):
        assert hash_password("same") != hash_password("same")


class TestPasswordPolicy:
    def test_warns_on_default_password(self, capsys, monkeypatch):
        import utils.jwt_utils as ju

        monkeypatch.setattr(
            ju,
            "USERS",
            {
                "admin": {"password": hash_password("123456"), "role": "admin", "dept": ""},
            },
        )
        check_password_policy()
        out = capsys.readouterr().out
        assert "admin" in out
        assert "123456" in out

    def test_warns_on_plaintext(self, capsys, monkeypatch):
        import utils.jwt_utils as ju

        monkeypatch.setattr(
            ju,
            "USERS",
            {
                "service": {"password": "plainpw", "role": "service", "dept": ""},
            },
        )
        check_password_policy()
        out = capsys.readouterr().out
        assert "service" in out
        assert "明文" in out
