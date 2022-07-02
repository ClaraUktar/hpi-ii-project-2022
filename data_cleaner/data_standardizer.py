import re
from typing import Tuple

from build.gen.bakdata.corporate.v2.cleaned_company_pb2 import CleanedCompany
from build.gen.bakdata.corporate.v2.company_pb2 import Company
from build.gen.bakdata.corporate.v2.deleted_company_pb2 import DeletedCompany
from build.gen.bakdata.corporate.v2.duplicate_company_pb2 import (
    DuplicateCompany,
)
from data_cleaner.neo4j_connector import Neo4jConnector
from data_cleaner.data_producer import CompanyProducer

UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
ADDRESS_REGEX = "(.*?\d{5} .*?)[\);,](.*)$"


class CompanyStandardizer:
    def __init__(self, producer: CompanyProducer):
        self.producer = producer
        self.connector = Neo4jConnector(
            "bolt://localhost:7687", "neo4j", "test"
        )

    def _clean_company_name(self, company: Company) -> str:
        should_delete_company = False
        company_name = company.name

        if bool(re.match(UUID_REGEX, company.name)):
            announcement = self.connector.get_announcement_for_company(
                company.name
            )

            if announcement["status"] == "STATUS_INACTIVE":
                # Get announcements with same refId
                related_announcements = (
                    self.connector.get_all_announcements_by_ref_id(
                        announcement
                    )
                )

                if len(related_announcements) > 0:
                    related_announcement_ids = [
                        announcement["id"]
                        for announcement in related_announcements
                    ]
                    original_company = self.connector.get_related_company_for_announcement_ids(
                        related_announcement_ids
                    )

                    if original_company is not None:
                        # Handle duplicate company
                        duplicate_company = DuplicateCompany()

                        duplicate_company.name = company.name
                        duplicate_company.originalName = original_company[
                            "name"
                        ]

                        # Only produce company to company-duplicate topic
                        # The company is not produced to the company-cleaned topic
                        # as we can assume that the original company is produced separately
                        self.producer.produce_duplicate_company(
                            duplicate_company
                        )

                        return
                    else:
                        should_delete_company = True

                else:
                    # Discard company, as we can't match it to anything
                    should_delete_company = True

            # else: connected announcement does not have STATUS_INACTIVE
            # this case does not exist in our data
            # if it would, a solution would be to use an updated regex
            # to parse the company name from the announcement information

        if should_delete_company:
            deleted_company = DeletedCompany()
            deleted_company.name = company.name

            self.producer.produce_deleted_company(deleted_company)
            return
        else:
            return company_name

    def _clean_company_address(self, company: Company) -> Tuple[str, str]:
        cleaned_address = company.address
        cleaned_description = company.description

        if cleaned_address and company.description == "":
            if "Gegenstand: " in company.address:
                splitted_address = company.address.split("Gegenstand: ", 1)
                cleaned_address = splitted_address[0]
                cleaned_description = splitted_address[1]
            elif bool(re.match(ADDRESS_REGEX, company.address)):
                result = re.match(ADDRESS_REGEX, company.address)
                cleaned_address = result.group(1)
                cleaned_description = result.group(2).strip()
            else:
                splitted_address = company.address.split(". ", 1)
                cleaned_address = splitted_address[0]
                if len(splitted_address) == 2:
                    cleaned_description = splitted_address[1]

        if company.patentAddress and not cleaned_address:
            # If company has a connection to patents but not to announcements
            cleaned_address = company.patentAddress
        elif company.patentAddress and cleaned_address:
            # If company has a connection to both, patents and announcements
            newest_patent_date = (
                self.connector.get_newest_patent_date_for_company(company.name)
            )
            newest_announcement_date = (
                self.connector.get_newest_announcement_date_for_company(
                    company.name
                )
            )
            if (
                newest_patent_date
                and newest_announcement_date
                and newest_patent_date > newest_announcement_date
            ):
                cleaned_address = company.patentAddress

        return cleaned_address, cleaned_description

    def _clean_company_country(self, company) -> str:
        if not company.country:
            return "DE"
        return company.country

    def _clean_company_capital(self, company):
        return company.capital

    def clean_company(self, company: Company) -> CleanedCompany:
        cleaned_company_name = self._clean_company_name(company)

        if cleaned_company_name:
            (
                cleaned_company_address,
                cleaned_company_description,
            ) = self._clean_company_address(company)
            cleaned_company_country = self._clean_company_country(company)
            cleaned_company_capital = self._clean_company_capital(company)

            cleaned_company = CleanedCompany()
            cleaned_company.name = cleaned_company_name
            cleaned_company.address = cleaned_company_address
            cleaned_company.country = cleaned_company_country
            cleaned_company.description = cleaned_company_description
            cleaned_company.capital = cleaned_company_capital

            self.producer.produce_cleaned_company(cleaned_company)
