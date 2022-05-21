from epo_crawler.epo_extractor import EpoExtractor
from epo_crawler.epo_parser import EpoParser
from dotenv import load_dotenv
import logging
import os
from time import sleep

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def run():
    load_dotenv()
    extractor = EpoExtractor()
    parser = EpoParser()

    id = "EP0000001"
    epo_json = extractor.fetch(id)

    logger.debug(epo_json)

    patent = parser.serialize(id, epo_json)

    logger.debug(patent)


if __name__ == "__main__":
    run()
