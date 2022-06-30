import logging

from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer
from confluent_kafka.serialization import StringSerializer

from build.gen.bakdata.corporate.v2.cleaned_company_pb2 import CleanedCompany
from build.gen.bakdata.corporate.v2.duplicate_company_pb2 import (
    DuplicateCompany,
)
from neo4j_crawler.constants import (
    SCHEMA_REGISTRY_URL,
    BOOTSTRAP_SERVER,
    TOPIC,
)

logger = logging.getLogger(__name__)


class CompanyProducer:
    """Produces Kafka events from cleaned or duplicate company protobuf objects"""

    def __init__(self):
        schema_registry_conf = {"url": SCHEMA_REGISTRY_URL}
        schema_registry_client = SchemaRegistryClient(schema_registry_conf)

        cc_protobuf_serializer = ProtobufSerializer(
            CleanedCompany,
            schema_registry_client,
            {"use.deprecated.format": True},
        )
        dc_protobuf_serializer = ProtobufSerializer(
            DuplicateCompany,
            schema_registry_client,
            {"use.deprecated.format": True},
        )

        cc_producer_conf = {
            "bootstrap.servers": BOOTSTRAP_SERVER,
            "key.serializer": StringSerializer("utf_8"),
            "value.serializer": cc_protobuf_serializer,
        }
        dc_producer_conf = {
            "bootstrap.servers": BOOTSTRAP_SERVER,
            "key.serializer": StringSerializer("utf_8"),
            "value.serializer": dc_protobuf_serializer,
        }

        self.cc_producer = SerializingProducer(cc_producer_conf)
        self.dc_producer = SerializingProducer(dc_producer_conf)

    def produce_cleaned_company(self, company: CleanedCompany):
        self.cc_producer.produce(
            topic=TOPIC + "-cleaned",
            partition=-1,
            key=str(company.name),
            value=company,
            on_delivery=self.delivery_report,
        )

        # It is a naive approach to flush after each produce this can be optimised
        self.cc_producer.poll()

    def produce_duplicate_company(self, company: DuplicateCompany):
        self.dc_producer.produce(
            topic=TOPIC + "-duplicate",
            partition=-1,
            key=str(company.name),
            value=company,
            on_delivery=self.delivery_report,
        )

        # It is a naive approach to flush after each produce this can be optimised
        self.dc_producer.poll()

    @staticmethod
    def delivery_report(err, msg):
        """
        Reports the failure or success of a message delivery.
        Args:
            err (KafkaError): The error that occurred on None on success.
            msg (Message): The message that was produced or failed.
        Note:
            In the delivery report callback the Message.key() and Message.value()
            will be the binary format as encoded by any configured Serializers and
            not the same object that was passed to produce().
            If you wish to pass the original object(s) for key and value to delivery
            report callback we recommend a bound callback or lambda where you pass
            the objects along.
        """
        if err is not None:
            logger.error(
                "Delivery failed for User record {}: {}".format(msg.key(), err)
            )
            return
        logger.info(
            "User record {} successfully produced to {} [{}] at offset {}".format(
                msg.key(), msg.topic(), msg.partition(), msg.offset()
            )
        )
