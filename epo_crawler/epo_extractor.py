import base64
from time import sleep
import os
import requests


class EpoExtractor:
    def __init__(self):
        self.access_token = None

    def extract(self):
        self.request_access_token()
        print(self.access_token)
        text = self.send_request()
        print(text)

    def request_access_token(self):
        consumer_key = os.environ.get("EPO_CONSUMER_KEY")
        consumer_secret = os.environ.get("EPO_CONSUMER_SECRET")
        
        if not (consumer_key and consumer_secret):
            return

        url = "https://ops.epo.org/3.2/auth/accesstoken"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = { "grant_type": "client_credentials" }

        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=data,
                auth=(consumer_key, consumer_secret)
            )

            if response.status_code != 200:
                print("Error ", response.text)
                return

            self.access_token = response.json()["access_token"]
        except Exception as ex:
            print(ex)


    def send_request(self) -> str:
        if not self.access_token:
            return
       
        id = "EP99203729"
        url = f"https://ops.epo.org/3.2/rest-services/register/application/epodoc/{id}/biblio"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        # For graceful crawling! Remove this at your own risk!
        sleep(0.5)
        return requests.get(url=url, headers=headers).text