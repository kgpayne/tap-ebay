"""Custom client handling, including eBayStream base class."""


from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone

import requests
from ebaysdk.exception import ConnectionError
from ebaysdk.finding import Connection as Finding
from ebaysdk.shopping import Connection as Shopping

logger = logging.getLogger(__name__)


class oAuth_token(object):
    def __init__(
        self,
        error=None,
        access_token=None,
        refresh_token=None,
        refresh_token_expiry=None,
        token_expiry=None,
    ):
        """
        token_expiry: datetime in UTC
        refresh_token_expiry: datetime in UTC
        """
        self.access_token = access_token
        self.token_expiry = token_expiry
        self.refresh_token = refresh_token
        self.refresh_token_expiry = refresh_token_expiry
        self.error = error

    def __str__(self):
        token_str = "{"
        if self.error != None:
            token_str += f'"error": "{self.error}"'
        elif self.access_token != None:
            token_str += (
                '"access_token": "'
                + self.access_token
                + '", "expires_in": "'
                + self.token_expiry.strftime("%Y-%m-%dT%H:%M:%S:%f")
                + '"'
            )
            if self.refresh_token != None:
                token_str += (
                    ', "refresh_token": "'
                    + self.refresh_token
                    + '", "refresh_token_expire_in": "'
                    + self.refresh_token_expiry.strftime("%Y-%m-%dT%H:%M:%S:%f")
                    + '"'
                )
        token_str += "}"
        return token_str


class eBayClient:
    def __init__(self, app_id, client_secret, redirect_uri):
        self.app_id = app_id
        self.client_id = app_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_finding_api(self, site_id="EBAY-US"):
        return Finding(appid=self.app_id, config_file=None, siteid=site_id)

    def get_shopping_api(self, site_id="EBAY-US"):
        token = self.get_shopping_api_token()
        return Shopping(
            appid=self.app_id,
            iaf_token=token.access_token,
            config_file=None,
            siteid=site_id,
        )

    def execute(self, api, verb, data: dict = {}):
        try:
            # headers = api.build_request_headers(verb)
            return api.execute(verb, data)
        except ConnectionError as e:
            logger.error(f"Connection failed: {e}\n{e.response.dict()}")
            raise e

    def _generate_request_headers(self):
        """Generate oauth request flow headers."""
        b64_encoded_credential = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        )
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_encoded_credential.decode('utf-8')}",
        }

    def _generate_application_request_body(self, scopes):
        return {
            "grant_type": "client_credentials",
            "redirect_uri": self.redirect_uri,
            "scope": scopes,
        }

    def get_application_token(self, api_endpoint, scopes):
        """Get application token.

        Stores result in token object, and returns token object
        """
        logger.info("Trying to get a new application access token ... ")

        headers = self._generate_request_headers()
        body = self._generate_application_request_body(" ".join(scopes))
        resp = requests.post(api_endpoint, data=body, headers=headers)
        content = json.loads(resp.content)
        token = oAuth_token()

        if resp.status_code == requests.codes.ok:
            token.access_token = content["access_token"]
            # set token expiration time 5 minutes before actual expire time
            token.token_expiry = (
                datetime.now(timezone.utc)
                + timedelta(seconds=int(content["expires_in"]))
            ) - timedelta(minutes=5)

        else:
            token.error = f"{str(resp.status_code)}: " + content["error_description"]
            logging.error(
                "Unable to retrieve token.  Status code: %s - %s",
                resp.status_code,
                requests.status_codes._codes[resp.status_code],
            )
            logging.error(
                "Error: %s - %s", content["error"], content["error_description"]
            )
        return token

    def get_shopping_api_token(self):
        return self.get_application_token(
            api_endpoint="https://api.ebay.com/identity/v1/oauth2/token",
            scopes=["https://api.ebay.com/oauth/api_scope"],
        )
