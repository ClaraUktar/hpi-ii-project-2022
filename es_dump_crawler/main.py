import click
import logging
import os
import io

from es_dump_crawler.es_dump_extractor import EsDumpExtractor
from es_dump_crawler.es_dump_parser import EsDumpParser
from epo_crawler.epo_producer import EpoProducer

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("-f", "--file", required=True, type=str, help="A path to an elasticdump file containing EPO patents.")
def run(file: str):
    input_file = io.open(file, "r", buffering=1, encoding="utf-8")
    extractor = EsDumpExtractor()
    parser = EsDumpParser()
    producer = EpoProducer()

    while input_file.readable():
        line = input_file.readline()

        if not line:
            break

        epo_json = extractor.extract(line)

        logger.info("Reading EPO data of publication with id {}".format(epo_json["publicationId"]))

        patent = parser.serialize(epo_json)

        if not patent:
            break

        producer.produce_to_topic(patent)

    input_file.close()


if __name__ == "__main__":
    run()
