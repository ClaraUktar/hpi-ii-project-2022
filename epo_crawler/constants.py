import enum

BOOTSTRAP_SERVER: str = "localhost:29092"
SCHEMA_REGISTRY_URL: str = "http://localhost:8081"
TOPIC: str = "patent-events"


class Party(str, enum.Enum):
    APPLICANT = "applicant"
    INVENTOR = "inventor"
    REPRESENTATIVE = "agent"
