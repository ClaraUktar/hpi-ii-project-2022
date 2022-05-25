import logging
from datetime import datetime
from epo_crawler.constants import Party

from build.gen.bakdata.corporate.v1.patent_pb2 import Patent


logger = logging.getLogger(__name__)


class EpoParser:
    """ Serializes EPO JSON data to Protobuf format. """

    def __init__(self):
        self.patent = None

    # === HELPERS ===
    @staticmethod
    def _apply_to_all(element, handle_element):
        """
        Applies a function `handle_element` to all elements of a list.
        This abstracts the format specificity of EPO JSON that a list property could be an array
        if containing multiple items or a plain object if only containing one item.
        """

        if isinstance(element, list):
            for item in element:
                handle_element(item)
        else:
            handle_element(element)

    @staticmethod
    def _apply_to_first(element, handle_element):
        """
        Applies a function `handle_element` to the first element of a list.
        This abstracts the format specificity of EPO JSON that a list property could be an array
        if containing multiple items or a plain object if only containing one item.
        """

        if isinstance(element, list):
            handle_element(element[0])
        else:
            handle_element(element)

    @staticmethod
    def _set_timestamp(element, date: str):
        """ Sets a protobuf timestamp instance by parsing an EPO date string of format YYYYMMDD. """
        if date:
            element.FromDatetime(datetime.strptime(date, "%Y%m%d"))

    # === DATA EXTRACTORS ===
    def _extract_status(self, raw_status):
        status = self.patent.statuses.add()
        status.code = int(raw_status["@status-code"])
        self._set_timestamp(status.changeDate, raw_status.get("@change-date", None))

    def _extract_document(self, raw_document):
        document = self.patent.documents.add()
        document.country = raw_document["reg:country"]["$"]
        document.language = raw_document.get("@lang", "")
        document.docNumber = raw_document["reg:doc-number"]["$"]
        document.kind = raw_document["reg:kind"]["$"]
        self._set_timestamp(document.date, raw_document.get("reg:date", {}).get("$", None))

    def _extract_application(self, raw_application):
        application = self.patent.application
        country = raw_application["reg:country"]["$"]
        doc_number = raw_application["reg:doc-number"]["$"]
        application.applicationId = f"{country}{doc_number}"
        self._set_timestamp(application.filingDate, raw_application["reg:date"]["$"])

    def _extract_party(self, party, raw_party):
        party.name = raw_party["reg:name"]["$"]
        party.country = raw_party["reg:address"]["reg:country"]["$"]

        address_fields = filter(lambda item: str(item[0]).startswith(
            "reg:address-"), raw_party["reg:address"].items())
        address = ", ".join(map(lambda adr: adr[1]["$"], address_fields))

        party.address = address

    def _extract_applicant(self, raw_applicant):
        applicant = self.patent.applicants.add()
        self._extract_party(applicant, raw_applicant)

    def _extract_inventor(self, raw_inventor):
        inventor = self.patent.inventors.add()
        self._extract_party(inventor, raw_inventor)

    def _extract_representative(self, raw_representative):
        representative = self.patent.representatives.add()
        self._extract_party(representative, raw_representative)

    def _extract_all_party_members(self, member: Party, raw_parties):
        if not member in [Party.APPLICANT, Party.INVENTOR, Party.REPRESENTATIVE]:
            return

        if f"reg:{member}s" in raw_parties:
            extractor = None

            if member == Party.APPLICANT:
                extractor = self._extract_applicant
            elif member == Party.INVENTOR:
                extractor = self._extract_inventor
            elif member == Party.REPRESENTATIVE:
                extractor = self._extract_representative

            # Assumption: We are only interested in the latest entries and therefore parse the first list entry only
            self._apply_to_first(
                raw_parties[f"reg:{member}s"],
                lambda raw_parties_latest: self._apply_to_all(
                    raw_parties_latest[f"reg:{member}"],
                    lambda raw_party: extractor(raw_party["reg:addressbook"])
                )
            )

    def _extract_designated_states(self, raw_states):
        states = []

        self._apply_to_all(raw_states, lambda s: states.append(s["$"]))
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
            raw_statuses = register_document["reg:ep-patent-statuses"]["reg:ep-patent-status"]
            self._apply_to_all(raw_statuses, lambda s: self._extract_status(s))

            bibliographic_data = register_document["reg:bibliographic-data"]

            # 3. Documents
            raw_documents = bibliographic_data["reg:publication-reference"]
            self._apply_to_all(raw_documents, lambda doc: self._extract_document(doc["reg:document-id"]))

            # 4. Application
            raw_application = bibliographic_data["reg:application-reference"]
            self._apply_to_first(raw_application, lambda a: self._extract_application(a["reg:document-id"]))

            # 5. Filing language
            self.patent.filingLanguage = bibliographic_data["reg:language-of-filing"]["$"]

            # 6. Applicants
            parties = bibliographic_data["reg:parties"]
            self._extract_all_party_members(Party.APPLICANT, parties)

            # 7. Inventors (can be optional)
            self._extract_all_party_members(Party.INVENTOR, parties)

            # 8. Representatives (can be optional)
            self._extract_all_party_members(Party.REPRESENTATIVE, parties)

            # 9. Designated states
            raw_states = bibliographic_data["reg:designation-of-states"]
            self._apply_to_first(raw_states, lambda s: self._extract_designated_states(s["reg:designation-pct"]["reg:regional"]["reg:country"]))

            # 10. Titles
            raw_titles = bibliographic_data["reg:invention-title"]
            self._extract_titles(raw_titles)

            return self.patent
        except Exception as ex:
            logger.error("Serializing EPO JSON failed", ex)
            return None
