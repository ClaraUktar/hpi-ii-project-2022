import logging
from time import sleep

import requests
from parsel import Selector

import re

from build.gen.bakdata.corporate.v1.corporate_pb2 import Announcement, Status
from rb_producer import RbProducer

log = logging.getLogger(__name__)

NAME_REGEX = "^(HRB [\w ]*: )?(.+?),"
ADDRESS_REGEX = "^(.+?), (.+? \d{5} .+?\)?)\."


class RbExtractor:
    def __init__(self, start_rb_id: int, state: str):
        self.rb_id = start_rb_id
        self.state = state
        self.producer = RbProducer()

    def extract(self):
        while True:
            try:
                log.info(
                    f"Sending Request for: {self.rb_id} and state: {self.state}"
                )
                text = self.send_request()
                if "Falsche Parameter" in text:
                    log.info("The end has reached")
                    break
                selector = Selector(text=text)
                announcement = Announcement()
                announcement.rb_id = self.rb_id
                announcement.state = self.state
                announcement.reference_id = (
                    self.extract_company_reference_number(selector)
                )
                event_type = selector.xpath(
                    "/html/body/font/table/tr[3]/td/text()"
                ).get()
                announcement.event_date = selector.xpath(
                    "/html/body/font/table/tr[4]/td/text()"
                ).get()
                announcement.id = f"{self.state}_{self.rb_id}"
                raw_text: str = selector.xpath(
                    "/html/body/font/table/tr[6]/td/text()"
                ).get()
                self.handle_events(announcement, event_type, raw_text)
                self.rb_id = self.rb_id + 1
                log.debug(announcement)
            except Exception as ex:
                log.error(f"Skipping {self.rb_id} in state {self.state}")
                log.error(f"Cause: {ex}")
                self.rb_id = self.rb_id + 1
                continue
        exit(0)

    def send_request(self) -> str:
        url = f"https://www.handelsregisterbekanntmachungen.de/skripte/hrb.php?rb_id={self.rb_id}&land_abk={self.state}"
        # For graceful crawling! Remove this at your own risk!
        sleep(0.5)
        return requests.get(url=url).text

    @staticmethod
    def extract_company_reference_number(selector: Selector) -> str:
        return (
            (
                selector.xpath(
                    "/html/body/font/table/tr[1]/td/nobr/u/text()"
                ).get()
            ).split(": ")[1]
        ).strip()

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
        if event_type == "Neueintragungen":
            self.handle_new_entries(announcement, raw_text)
        elif event_type == "Veränderungen":
            self.handle_changes(announcement, raw_text)
        elif event_type == "Löschungen":
            self.handle_deletes(announcement, raw_text)

    def handle_new_entries(
        self, announcement: Announcement, raw_text: str
    ) -> Announcement:
        log.debug(f"New company found: {announcement.id}")
        announcement.event_type = "create"
        announcement.information = raw_text

        company = announcement.company
        name = re.search(NAME_REGEX, raw_text)
        address = re.search(ADDRESS_REGEX, raw_text)

        if name is None or address is None:
            raise ValueError("Name or address could not be extracted.")

        company.name = name.group(2)
        company.address = address.group(2)
        company.description = self.extract_description(raw_text)
        company.capital = float(
            self.extract_capital(raw_text).replace(".", "").replace(",", ".")
        )

        announcement.status = Status.STATUS_ACTIVE
        self.producer.produce_to_topic(announcement=announcement)

    def handle_changes(self, announcement: Announcement, raw_text: str):
        log.debug(f"Changes are made to company: {announcement.id}")
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

        self.producer.produce_to_topic(announcement=announcement)

    def handle_deletes(self, announcement: Announcement, raw_text: str):
        log.debug(f"Company {announcement.id} is inactive")
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

        self.producer.produce_to_topic(announcement=announcement)
