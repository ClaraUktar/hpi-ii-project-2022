from typing import List
from neo4j import GraphDatabase
from datetime import datetime

from build.gen.bakdata.corporate.v1.corporate_pb2 import Announcement
from build.gen.bakdata.corporate.v2.company_pb2 import Company


class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_announcement_for_company(self, company_id: str) -> Announcement:
        announcement = None

        with self.driver.session() as session:
            announcement = session.read_transaction(
                self._read_first_announcement_for_company,
                company_id,
            )

        return announcement

    def get_all_announcements_by_ref_id(
        self, announcement: Announcement
    ) -> List[Announcement]:
        announcements = []

        with self.driver.session() as session:
            announcements = session.read_transaction(
                self._read_all_announcements_by_ref_id, announcement
            )

        return announcements

    def get_related_company_for_announcement_ids(
        self, announcement_ids: List[str]
    ) -> Company:
        company = None

        with self.driver.session() as session:
            company = session.read_transaction(
                self._read_company_related_to_announcement_ids,
                announcement_ids,
            )

        return company

    def get_newest_patent_date_for_company(
        self, company_name: str
    ) -> datetime:
        date = None

        with self.driver.session() as session:
            date = session.read_transaction(
                self._read_newest_patent_date_for_company, company_name
            )

        return date

    def get_newest_announcement_date_for_company(
        self, company_name: str
    ) -> datetime:
        date = None

        with self.driver.session() as session:
            date = session.read_transaction(
                self._read_newest_announcement_date_for_company, company_name
            )

        return date

    @staticmethod
    def _read_first_announcement_for_company(tx, company_id):
        result = tx.run(
            f'MATCH (:Company{{name: "{company_id}"}})<--(a:Announcement) RETURN a{{.*}}'
        )

        return result.single()["a"]

    @staticmethod
    def _read_all_announcements_by_ref_id(tx, announcement):
        result = tx.run(
            f"""
            MATCH (a:Announcement {{refId: "{announcement["refId"]}"}})
            WHERE a.id <> "{announcement["id"]}"
                AND a.eventType <> "delete"
                AND a.state = "{announcement["state"]}"
            RETURN a{{.*}}
            """
        )

        return [dict(announcement["a"]) for announcement in result]

    @staticmethod
    def _read_company_related_to_announcement_ids(
        tx, announcement_ids: List[str]
    ):
        result = tx.run(
            f"""
            MATCH (c:Company)<--(a:Announcement)
            WHERE a.id in {announcement_ids}
            RETURN DISTINCT c{{.*}}
            """
        )

        return result.single()["c"]

    @staticmethod
    def _read_newest_patent_date_for_company(tx, company_id: str):
        result = tx.run(
            f"""
            MATCH (:Company{{name: "{company_id}"}})<--(:Patent)-->(s:Status)
            WHERE s.changeDate <> ""
            RETURN apoc.coll.max(collect(datetime(s.changeDate))) as newestDate
            """
        )

        return result.single()["newestDate"]

    @staticmethod
    def _read_newest_announcement_date_for_company(tx, company_id: str):
        result = tx.run(
            f"""
            MATCH (:Company{{name: "{company_id}"}})<--(a:Announcement)
            RETURN apoc.coll.max(
                collect(datetime(
                    {{epochmillis:apoc.date.parse(a.eventDate, "ms", "dd.MM.yyyy")}}
                ))
            ) as newestDate
        """
        )

        return result.single()["newestDate"]
