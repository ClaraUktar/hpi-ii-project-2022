import logging
import os
from data_cleaner.data_standardizer import CompanyStandardizer
from data_cleaner.data_consumer import CompanyConsumer
from data_cleaner.data_producer import CompanyProducer

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def run():
    consumer = CompanyConsumer()
    producer = CompanyProducer()
    cleaner = CompanyStandardizer(producer)

    while True:
        company = consumer.consume_from_topic()

        if company is None:
            break

        logger.info(
            f"Consumed message {company.key()} with offset {company.offset()}"
        )
        cleaned_company = cleaner.clean_company(company.value())

        producer.produce_cleaned_company(cleaned_company)

    cleaner.connector.close()


if __name__ == "__main__":
    run()
