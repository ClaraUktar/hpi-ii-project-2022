import logging
import os
from data_cleaner.data_standardizer import CompanyStandardizer
from data_cleaner.data_consumer import CompanyConsumer
from data_cleaner.data_producer import CleanedCompanyProducer

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def run():
    consumer = CompanyConsumer()
    cleaner = CompanyStandardizer()
    producer = CleanedCompanyProducer()

    company = consumer.consume_from_topic()
    cleaned_company = cleaner.clean_company(company.value())
    producer.produce_to_topic(cleaned_company)


if __name__ == "__main__":
    run()
