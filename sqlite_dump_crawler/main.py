import click
import logging
import os
import sqlite3

from sqlite_dump_crawler.sqlite_dump_parser import SqliteDumpParser
from rb_crawler.rb_producer import RbProducer

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("-f", "--file", required=True, type=str, help="A path to a SQLite file containing HRB announcements.")
@click.option("-s", "--skip", type=int, default=0, help="A number how much entries should be skipped")
def run(file: str, skip: int):
    parser = SqliteDumpParser()
    producer = RbProducer()

    con = sqlite3.connect(file)
    cur = con.cursor()

    for row in cur.execute("SELECT * FROM 'corporate-events' LIMIT -1 OFFSET ?", (skip,)):
        announcement = parser.serialize(row)

        if not announcement:
            continue

        producer.produce_to_topic(announcement)

    con.close()


if __name__ == "__main__":
    run()
