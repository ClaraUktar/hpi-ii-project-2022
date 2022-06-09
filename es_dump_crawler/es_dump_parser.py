import logging
from google.protobuf.json_format import ParseDict

from build.gen.bakdata.corporate.v1.patent_pb2 import Patent


logger = logging.getLogger(__name__)


class EsDumpParser:
    """ Serializes EPO JSON data to Protobuf format. """

    def serialize(self, epo_json) -> Patent:
        try:
            patent = ParseDict(epo_json, Patent())

            return patent
        except Exception as ex:
            logger.error("Serializing EPO JSON failed", ex)
            return None
