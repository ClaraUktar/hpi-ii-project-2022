from typing import List
from neo4j import GraphDatabase

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

    def get_all_announcements_for_ref_id(
        self, ref_id: str, announcement_id: str
    ) -> List[Announcement]:
        announcements = []

        with self.driver.session() as session:
            announcements = session.read_transaction(
                self._read_all_annoucements_for_ref_id_except_id,
                ref_id,
                announcement_id,
            )

        return announcements

    def get_related_company_for_announcement_ids(
        self, announcement_ids: List[str]
    ) -> Company:
        company = None

        with self.driver.session() as session:
            company = session.read_transaction(
                self._read_company_related_to_annoucement_ids,
                announcement_ids,
            )

        return company

    @staticmethod
    def _read_first_announcement_for_company(tx, company_id):
        result = tx.run(
            f'MATCH (:Company{{name: "{company_id}"}})<-[:IS_MADE_FOR]-(a:Announcement) RETURN a{{.*}}'
        )

        return result.single()["a"]

    @staticmethod
    def _read_all_annoucements_for_ref_id_except_id(tx, ref_id, id):
        result = tx.run(
            f"""
            MATCH (a:Announcement{{refId: "{ref_id}"}})
            WHERE a.id <> "{id}"
                AND a.eventType <> "delete"
            RETURN a{{.*}}
            """
        )

        return [dict(announcement["a"]) for announcement in result]

    @staticmethod
    def _read_company_related_to_annoucement_ids(
        tx, announcement_ids: List[str]
    ):
        result = tx.run(
            f"""
            MATCH (c:Company)<--(a:Announcement)
            WHERE a.id in {announcement_ids}
            RETURN c{{.*}}
            """
        )

        return result.single()["c"]
