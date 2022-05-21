from datetime import datetime
import logging

from build.gen.bakdata.corporate.v1.patent_pb2 import Patent


log = logging.getLogger(__name__)


class EpoParser:
    """ Serializes EPO JSON data to Protobuf format. """

    def __init__(self):
        self.patent = None

    # === HELPERS ===
    @staticmethod
    def _apply_to_children(parent, child_name: str, handle_child):
        """
        Applies a function `handle_child` to all elements of a list.
        This abstracts the format specificity of EPO JSON that a list property could be an array
        if containing multiple items or a plain object if only containing one item.
        """

        if isinstance(parent, list):
            for child in parent:
                handle_child(child[child_name])
        else:
            handle_child(parent[child_name])

    @staticmethod
    def _set_timestamp(element, date: str):
        """ Sets a protobuf timestamp instance by parsing an EPO date string of format YYYYMMDD. """

        element.FromDatetime(datetime.strptime(date, "%Y%m%d"))

    # === DATA EXTRACTORS ===
    def _extract_status(self, raw_status):
        status = self.patent.statuses.add()
        status.code = int(raw_status["@status-code"])

        if raw_status["@change-date"]:
            self._set_timestamp(status.changeDate, raw_status["@change-date"])

    def _extract_document(self, raw_document):
        document = self.patent.documents.add()
        document.country = raw_document["reg:country"]["$"]
        document.language = raw_document["@lang"]
        document.docNumber = raw_document["reg:doc-number"]["$"]
        document.kind = raw_document["reg:kind"]["$"]
        self._set_timestamp(document.date, raw_document["reg:date"]["$"])

    def _extract_application(self, raw_application):
        application = self.patent.application
        country = raw_application["reg:country"]["$"]
        doc_number = raw_application["reg:doc-number"]["$"]
        application.applicationId = f"{country}{doc_number}"
        self._set_timestamp(application.filingDate, raw_application["reg:date"]["$"])

    def _extract_party(self, party, raw_party):
        party.name = raw_party["reg:addressbook"]["reg:name"]["$"]
        party.address = raw_party["reg:addressbook"]["reg:address"]["reg:address-1"]["$"]
        party.zipCode = raw_party["reg:addressbook"]["reg:address"]["reg:address-2"]["$"]
        party.country = raw_party["reg:addressbook"]["reg:address"]["reg:country"]["$"]

    def _extract_applicant(self, raw_applicant):
        applicant = self.patent.applicants.add()
        self._extract_party(applicant, raw_applicant)

    def _extract_inventor(self, raw_inventor):
        inventor = self.patent.inventors.add()
        self._extract_party(inventor, raw_inventor)

    def _extract_representative(self, raw_representative):
        representative = self.patent.representatives.add()
        self._extract_party(representative, raw_representative)

    def _extract_designated_states(self, raw_states):
        states = map(lambda s: s["$"], raw_states)
        self.patent.designatedStates.extend(states)

    def _extract_titles(self, raw_titles):
        for raw_title in raw_titles:
            self.patent.titles[raw_title["@lang"]] = raw_title["$"]

    def serialize(self, id: str, epo_json) -> Patent:
        try:
            self.patent = Patent()

            # 1. Publication ID
            self.patent.publicationId = id

            register_document = epo_json["ops:world-patent-data"]["ops:register-search"]["reg:register-documents"]["reg:register-document"]

            # 2. Statuses
            raw_statuses = register_document["reg:ep-patent-statuses"]
            self._apply_to_children(
                raw_statuses, "reg:ep-patent-status", lambda status: self._extract_status(status))

            bibliographic_data = register_document["reg:bibliographic-data"]

            # 3. Documents
            raw_documents = bibliographic_data["reg:publication-reference"]
            self._apply_to_children(
                raw_documents, "reg:document-id", lambda doc: self._extract_document(doc))

            # 4. Application
            raw_application = bibliographic_data["reg:application-reference"]["reg:document-id"]
            self._extract_application(raw_application)

            # 5. Filing language
            self.patent.filingLanguage = bibliographic_data["reg:language-of-filing"]["$"]

            # 6. Applicants
            raw_applicants = bibliographic_data["reg:parties"]["reg:applicants"]
            self._apply_to_children(raw_applicants, "reg:applicant",
                                    lambda applicant: self._extract_applicant(applicant))

            # 7. Inventors
            raw_inventors = bibliographic_data["reg:parties"]["reg:inventors"]
            self._apply_to_children(raw_inventors, "reg:inventor",
                                    lambda inventor: self._extract_inventor(inventor))

            # 8. Representatives
            raw_representatives = bibliographic_data["reg:parties"]["reg:agents"]
            self._apply_to_children(raw_representatives, "reg:agent",
                                    lambda representative: self._extract_representative(representative))

            # 9. Designated states
            raw_states = bibliographic_data["reg:designation-of-states"]["reg:designation-pct"]["reg:regional"]["reg:country"]
            self._extract_designated_states(raw_states)

            # 10. Titles
            raw_titles = bibliographic_data["reg:invention-title"]
            self._extract_titles(raw_titles)

            return self.patent
        except Exception as ex:
            log.error("Serializing EPO JSON failed", ex)
            return None
