from datetime import datetime, timezone
import json


class EsDumpExtractor:
    """ Extracts patent data as JSON from a string of a elasticdump file """

    @staticmethod
    def _parse_date(ts: int) -> str:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()

    def extract(self, line: str):
        # Pre-processing
        line = line.replace("_changeDate_0", "changeDate")

        # Parsing
        parsed_line = json.loads(line)
        result = parsed_line["_source"]

        # Post-processing
        for status in result["statuses"]:
            if status["changeDate"]:
                status["changeDate"] = self._parse_date(status["changeDate"]["changeDate"])

        for document in result["documents"]:
            if document["date"]:
                document["date"] = self._parse_date(document["date"])

        if result["application"]["filingDate"]:
            result["application"]["filingDate"] = self._parse_date(result["application"]["filingDate"])

        return result
