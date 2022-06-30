import re

from build.gen.bakdata.corporate.v2.cleaned_company_pb2 import CleanedCompany
from build.gen.bakdata.corporate.v2.company_pb2 import Company
from build.gen.bakdata.corporate.v2.deleted_company_pb2 import DeletedCompany
from build.gen.bakdata.corporate.v2.duplicate_company_pb2 import (
    DuplicateCompany,
)
from data_cleaner.neo4j_connector import Neo4jConnector
from data_cleaner.data_producer import CompanyProducer

UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


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
            else:
                # Check for messed up regex (ideally never happens)
                print(company)
                print(announcement)
                raise Exception("Found company with active announcement")

                # TODO: Set company_name appropriately

        if should_delete_company:
            deleted_company = DeletedCompany()
            deleted_company.name = company.name

            self.producer.produce_deleted_company(deleted_company)
        else:
            return company_name

    def clean_company(self, company: Company) -> CleanedCompany:
        # TODO: Add cleaning logic
        cleaned_company_name = self._clean_company_name(company)

        if cleaned_company_name:
            cleaned_company = CleanedCompany()
            cleaned_company.name = cleaned_company_name
            cleaned_company.address = company.address
            cleaned_company.country = company.country
            cleaned_company.description = company.description
            cleaned_company.capital = company.capital

            self.producer.produce_cleaned_company(cleaned_company)
