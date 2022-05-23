import click
import logging
import os

from epo_crawler.epo_extractor import EpoExtractor
from epo_crawler.epo_parser import EpoParser
from epo_crawler.epo_producer import EpoProducer
from dotenv import load_dotenv
from time import sleep

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("-i", "--id", required=True, type=click.IntRange(1, 9999999), help="The patent ID (publication) to initialize the crawl from (number between 1 and 9999999)")
@click.option("-s", "--single", is_flag=True, default=False, help="Whether a single patent should be crawled. Useful for debugging.")
def run(id: int, single: bool):
    load_dotenv()
    extractor = EpoExtractor()
    parser = EpoParser()
    producer = EpoProducer()

    while True:
        epo_id = f"EP{str(id).zfill(7)}"
        logger.info(f"Fetching EPO data of publication with id {epo_id}")

        epo_json = extractor.fetch(epo_id)

        if single:
            logger.debug(epo_json)

        if not single and not epo_json:
            continue

        patent = parser.serialize(epo_id, epo_json)

        if single:
            logger.debug(patent)

        producer.produce_to_topic(patent)

        if single:
            break

        sleep(0.5)
        id += 1


if __name__ == "__main__":
    run()
