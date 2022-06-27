import logging

from confluent_kafka import DeserializingConsumer, TopicPartition
from confluent_kafka.schema_registry.protobuf import ProtobufDeserializer
from confluent_kafka.serialization import StringDeserializer

from build.gen.bakdata.corporate.v2 import company_pb2
from build.gen.bakdata.corporate.v2.company_pb2 import Company
from neo4j_crawler.constants import (
    BOOTSTRAP_SERVER,
    TOPIC,
)

logger = logging.getLogger(__name__)


class CompanyConsumer:
    """Consumes Kafka events from Company protobuf objects"""

    def __init__(self):
        protobuf_deserializer = ProtobufDeserializer(
            company_pb2.Company,
            {"use.deprecated.format": True},
        )

        consumer_conf = {
            "bootstrap.servers": BOOTSTRAP_SERVER,
            "group.id": TOPIC,
            "key.deserializer": StringDeserializer("utf_8"),
            "value.deserializer": protobuf_deserializer,
        }

        self.consumer = DeserializingConsumer(consumer_conf)
        self.consumer.assign([TopicPartition(TOPIC, partition=0, offset=0)])

    def consume_from_topic(self) -> Company:
        return self.consumer.poll(timeout=5)
