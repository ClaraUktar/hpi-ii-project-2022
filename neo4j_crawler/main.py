import logging
import os
from neo4j_crawler.neo4j_extractor import Neo4jExtractor
from neo4j_crawler.neo4j_producer import CompanyProducer
from google.protobuf.json_format import ParseDict

from build.gen.bakdata.corporate.v2.company_pb2 import Company

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

producer = CompanyProducer()


def parse_company(company_json) -> Company:
    try:
        company = ParseDict(company_json, Company())

        producer.produce_to_topic(company)
    except Exception as ex:
        logger.error("Serializing EPO JSON failed", ex)
        return None


def run():
    extractor = Neo4jExtractor("bolt://localhost:7687", "neo4j", "test")
    extractor.get_companies(parse_company)
    extractor.close()


if __name__ == "__main__":
    run()
