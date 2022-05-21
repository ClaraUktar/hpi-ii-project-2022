import logging
import os
import requests
from sys import exit

logger = logging.getLogger(__name__)


class EpoExtractor:
    """ Fetches patent data as JSON from EPO portal for further processing. """

    def __init__(self):
        self._request_access_token()

    def _request_access_token(self):
        # Reset access token
        self.access_token = None

        consumer_key = os.environ.get("EPO_CONSUMER_KEY")
        consumer_secret = os.environ.get("EPO_CONSUMER_SECRET")

        if not (consumer_key and consumer_secret):
            logger.error(
                "No consumer key found for request authorization. Check your .env file for EPO_CONSUMER_KEY and EPO_CONSUMER_SECRET.")
            exit(1)

        url = "https://ops.epo.org/3.2/auth/accesstoken"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(
                url,
                data,
                auth=(consumer_key, consumer_secret),
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    f"Requesting access token failed with status {response.status_code}, message: {response.text}")
                exit(1)

            self.access_token = response.json()["access_token"]
        except Exception as ex:
            logger.error(f"Unexpected error during requesting access token: {ex}")
            exit(1)

    def _send_request(self, id: str):
        try:
            if not self.access_token:
                return

            url = f"https://ops.epo.org/3.2/rest-services/register/publication/epodoc/{id}/biblio"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }

            response = requests.get(url=url, headers=headers)

            if response.status_code == 200:
                return response.json()
            if response.status_code == 400:
                # if access token is expired, try to request a new one and retry
                self._request_access_token()
                return self._send_request(id)
            elif response.status_code == 403 and response.headers.get("X-Rejection-Reason") == "RegisteredQuotaPerWeek":
                logger.error("Weekly request quota exhausted, stopping program.")
                exit(1)
            elif response.status_code == 404:
                # if 404, skip to next (return nothing)
                return None
            else:
                logger.error(
                    f"Unexpected response: status {response.status_code}, message {response.text}")
                exit(1)
        except Exception as ex:
            logger.error(f"Unexpected error during requesting EPO data: {ex}")
            exit(1)

    def fetch(self, id: str):
        result = self._send_request(id)

        return result
