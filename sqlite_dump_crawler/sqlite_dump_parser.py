import logging
import re

from build.gen.bakdata.corporate.v1.corporate_pb2 import Announcement, Status


NAME_REGEX = "^(HRB [\w ]*: )?(.+?),"
ADDRESS_REGEX = "^(.+?), (.+? \d{5} .+?\)?)\."

logger = logging.getLogger(__name__)


class SqliteDumpParser:
    """ Serializes HRB SQLite row data to Protobuf format. """

    def serialize(self, row) -> Announcement:
        try:
            (id, rb_id, state, reg_auth, ref_id, event_date, event_type, status, information) = row

            logger.info("Reading HRB data of state {} with id {}".format(state, rb_id))

            announcement = Announcement()
            announcement.id = id
            announcement.rb_id = rb_id
            announcement.state = state
            announcement.reference_id = ref_id
            announcement.event_date = event_date

            self.handle_events(announcement, event_type, information)

            return announcement
        except Exception as ex:
            logger.error("Serializing HRB entry failed", ex)
            return None

    @staticmethod
    def extract_description(raw_text: str) -> str:
        result = ""

        if "Gegenstand:" in raw_text:
            result = re.search("Gegenstand: (.+)\. .+(EUR|DM)", raw_text)
        elif "Geschäftsanschrift:" in raw_text:
            result = re.search(
                "Geschäftsanschrift: .+?\. (.+?)\. ([\w ]*: )?.+? (EUR|DM)",
                raw_text,
            )

        if result:
            return result.group(1)
        return ""

    @staticmethod
    def extract_capital(raw_text: str) -> str:
        result = re.search("[\.:] ([0-9,\.]+) (EUR|DM)", raw_text)
        if result is None:
            return "0"
        return result.group(1)

    def handle_events(self, announcement, event_type, raw_text):
        if event_type == "create":
            self.handle_new_entries(announcement, raw_text)
        elif event_type == "update":
            self.handle_changes(announcement, raw_text)
        elif event_type == "delete":
            self.handle_deletes(announcement, raw_text)

    def handle_new_entries(self, announcement: Announcement, raw_text: str):
        logger.debug(f"New company found: {announcement.id}")
        announcement.event_type = "create"
        announcement.status = Status.STATUS_ACTIVE
        announcement.information = raw_text

        company = announcement.company
        name = re.search(NAME_REGEX, raw_text)
        address = re.search(ADDRESS_REGEX, raw_text)

        if name is None or address is None:
            raise ValueError("Name or address could not be extracted.")

        company.name = name.group(2)
        company.address = address.group(2)
        company.description = self.extract_description(raw_text)
        company.capital = float(self.extract_capital(raw_text).replace(".", "").replace(",", "."))

    def handle_changes(self, announcement: Announcement, raw_text: str):
        logger.debug(f"Changes are made to company: {announcement.id}")
        announcement.event_type = "update"
        announcement.status = Status.STATUS_ACTIVE
        announcement.information = raw_text

        company = announcement.company
        name = re.search(NAME_REGEX, raw_text)
        address = re.search(ADDRESS_REGEX, raw_text)

        if name is None or address is None:
            raise ValueError

        company.name = name.group(2)
        company.address = address.group(2)

    def handle_deletes(self, announcement: Announcement, raw_text: str):
        logger.debug(f"Company {announcement.id} is inactive")
        announcement.event_type = "delete"
        announcement.status = Status.STATUS_INACTIVE

        announcement.information = raw_text

        company = announcement.company
        name = re.search(NAME_REGEX, raw_text)
        address = re.search(ADDRESS_REGEX, raw_text)

        if name is None or address is None:
            raise ValueError

        company.name = name.group(2)
        company.address = address.group(2)
