import click
import logging
import os
import re

from epo_crawler.epo_extractor import EpoExtractor
from epo_crawler.epo_parser import EpoParser
from epo_crawler.epo_producer import EpoProducer
from dotenv import load_dotenv
from time import sleep

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def validate_id(ctx, param, value):
    if re.match("^EP[0-9]{6}[1-9]", value):
        return value
    else:
        raise click.BadParameter(
            "Parameter --id must be in format EPNNNNNNN where N is a digit between 0 and 9.")


@click.command()
@click.option("-i", "--id", required=True, callback=validate_id, help="The patent ID (publication) to initialize the crawl from (format: EPNNNNNNN where N is a digit between 0 and 9)")
def run(id: str):
    load_dotenv()
    extractor = EpoExtractor()
    parser = EpoParser()
    producer = EpoProducer()

    id_num = int(id[2:])

    while True:
        id = f"EP{str(id_num).zfill(7)}"
        logger.info(f"Fetching EPO data of publication with id {id}")

        epo_json = extractor.fetch(id)

        if not epo_json:
            continue

        patent = parser.serialize(id, epo_json)

        producer.produce_to_topic(patent)

        sleep(0.5)
        id_num += 1


if __name__ == "__main__":
    run()
