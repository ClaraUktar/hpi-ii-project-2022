from datetime import datetime
from time import sleep
import os
from typing import Any
import requests

from build.gen.bakdata.corporate.v1.patent_pb2 import Patent, Status


class EpoExtractor:
    def __init__(self):
        self.access_token = None
        self.current_id = "EP0000001"
        self.patent = None

    # === HELPERS ===
    def apply_to_children(self, parent, child_name: str, handle_child):
        if isinstance(parent, list):
            for child in parent:
                handle_child(child[child_name])

        else:
            handle_child(parent[child_name])

    def set_timestamp(self, element, date: str):
        element.FromDatetime(datetime.strptime(date, "%Y%m%d"))

    # === DATA EXTRACTORS ===
    def extract_status(self, raw_status):
        status = self.patent.statuses.add()
        status.code = int(raw_status["@status-code"])

        if raw_status["@change-date"]:
            self.set_timestamp(status.changeDate, raw_status["@change-date"])

    def extract_document(self, raw_document):
        document = self.patent.documents.add()
        document.country = raw_document["reg:country"]["$"]
        document.language = raw_document["@lang"]
        document.docNumber = raw_document["reg:doc-number"]["$"]
        document.kind = raw_document["reg:kind"]["$"]
        self.set_timestamp(document.date, raw_document["reg:date"]["$"])

    def extract_application(self, raw_application):
        application = self.patent.application
        country = raw_application["reg:country"]["$"]
        doc_number = raw_application["reg:doc-number"]["$"]
        application.applicationId = f"{country}{doc_number}"
        self.set_timestamp(application.filingDate, raw_application["reg:date"]["$"])

    def extract_party(self, party, raw_party):
        party.name = raw_party["reg:addressbook"]["reg:name"]["$"]
        party.address = raw_party["reg:addressbook"]["reg:address"]["reg:address-1"]["$"]
        party.zipCode = raw_party["reg:addressbook"]["reg:address"]["reg:address-2"]["$"]
        party.country = raw_party["reg:addressbook"]["reg:address"]["reg:country"]["$"]

    def extract_applicant(self, raw_applicant):
        applicant = self.patent.applicants.add()
        self.extract_party(applicant, raw_applicant)

    def extract_inventor(self, raw_inventor):
        inventor = self.patent.inventors.add()
        self.extract_party(inventor, raw_inventor)

    def extract_representative(self, raw_representative):
        representative = self.patent.representatives.add()
        self.extract_party(representative, raw_representative)

    def extract_designated_states(self, raw_states):
        states = map(lambda s: s["$"], raw_states)
        self.patent.designatedStates.extend(states)

    def extract_titles(self, raw_titles):
        for raw_title in raw_titles:
            self.patent.titles[raw_title["@lang"]] = raw_title["$"]

    def extract(self):
        self.request_access_token()
        result = self.send_request()

        self.patent = Patent()

        # 1. Publication ID
        self.patent.publicationId = self.current_id

        register_document = result["ops:world-patent-data"]["ops:register-search"]["reg:register-documents"]["reg:register-document"]

        # 2. Statuses
        raw_statuses = register_document["reg:ep-patent-statuses"]
        self.apply_to_children(raw_statuses, "reg:ep-patent-status", lambda status: self.extract_status(status))

        bibliographic_data = register_document["reg:bibliographic-data"]

        # 3. Documents
        raw_documents = bibliographic_data["reg:publication-reference"]
        self.apply_to_children(raw_documents, "reg:document-id", lambda doc: self.extract_document(doc))

        # 4. Application
        raw_application = bibliographic_data["reg:application-reference"]["reg:document-id"]
        self.extract_application(raw_application)

        # 5. Filing language
        self.patent.filingLanguage = bibliographic_data["reg:language-of-filing"]["$"]

        # 6. Applicants
        raw_applicants = bibliographic_data["reg:parties"]["reg:applicants"]
        self.apply_to_children(raw_applicants, "reg:applicant", lambda applicant: self.extract_applicant(applicant))

        # 7. Inventors
        raw_inventors = bibliographic_data["reg:parties"]["reg:inventors"]
        self.apply_to_children(raw_inventors, "reg:inventor", lambda inventor: self.extract_inventor(inventor))

        # 8. Representatives
        raw_representatives = bibliographic_data["reg:parties"]["reg:agents"]
        self.apply_to_children(raw_representatives, "reg:agent", lambda representative: self.extract_representative(representative))

        # 9. Designated states
        raw_states = bibliographic_data["reg:designation-of-states"]["reg:designation-pct"]["reg:regional"]["reg:country"]
        self.extract_designated_states(raw_states)

        # 10. Titles
        raw_titles = bibliographic_data["reg:invention-title"]
        self.extract_titles(raw_titles)

        print(self.patent)

    def request_access_token(self):
        consumer_key = os.environ.get("EPO_CONSUMER_KEY")
        consumer_secret = os.environ.get("EPO_CONSUMER_SECRET")

        if not (consumer_key and consumer_secret):
            print("Warning: No consumer key found for request authorization")
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


    def send_request(self) -> Any:
        if not self.access_token:
            return

        url = f"https://ops.epo.org/3.2/rest-services/register/publication/epodoc/{self.current_id}/biblio"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        # For graceful crawling! Remove this at your own risk!
        sleep(0.5)
        return requests.get(url=url, headers=headers).json()
