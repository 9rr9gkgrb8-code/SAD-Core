"""Hosted private-alpha signup extension. Keeps public role selection impossible."""

import re
from api import SadApiService
from signup_invites import SignupInviteStore


class SignupSadApiService(SadApiService):
    def __init__(self, *args, signup_invites=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.signup_invites = signup_invites or SignupInviteStore()

    def dispatch(self, method, path, headers, body):
        # Invite redemption is the only unauthenticated account-creation path.
        if method == "POST" and path == "/v1/signup":
            username = body.get("username", "")
            password = body.get("password", "")
            invite_code = body.get("invite_code", "")
            guardian_consent = body.get("guardian_consent") is True
            self.signup_invites.consume(invite_code, guardian_consent=guardian_consent)
            account = self.auth.create_invited_student(username, password)
            token = self.auth.login(username, password)
            if not token:
                raise PermissionError("Student account was created but automatic sign-in failed.")
            return 201, {"token": token, "account": account}

        # Owner-only invite administration uses the existing account:manage authority.
        if method == "GET" and path == "/v1/signup/invites":
            token = self.token(headers)
            self.auth.require(token, "account:manage")
            return 200, {"invites": self.signup_invites.list()}
        if method == "POST" and path == "/v1/signup/invites":
            token = self.token(headers)
            owner = self.auth.require(token, "account:manage")
            invite = self.signup_invites.create(
                owner["account_id"],
                expires_minutes=body.get("expires_minutes", 10080),
                max_uses=body.get("max_uses", 1),
                guardian_required=body.get("guardian_required", True),
            )
            return 201, invite
        match = re.fullmatch(r"/v1/signup/invites/([0-9a-f-]+)/revoke", path)
        if method == "POST" and match:
            token = self.token(headers)
            self.auth.require(token, "account:manage")
            return 200, self.signup_invites.revoke(match.group(1))
        return super().dispatch(method, path, headers, body)
