import logging
import os
import requests
import requests.adapters
from sys import exit

logger = logging.getLogger(__name__)

# We have to increase the maximum pool size for connections as it otherwise might happen
# that the crawler exits after some hundred requests. Also, it seems to improve performance
# in terms of request/response time.
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_maxsize=100)
session.mount('https://', adapter)


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
            response = session.post(
                url,
                data,
                auth=(consumer_key, consumer_secret),
                headers=headers,
                timeout=10
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
                logger.warning(f"Access token not set, skipping request ({id})")
                return

            url = f"https://ops.epo.org/3.2/rest-services/register/publication/epodoc/{id}/biblio"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }

            response = session.get(url=url, headers=headers, timeout=10)

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
