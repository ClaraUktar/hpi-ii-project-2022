from neo4j import GraphDatabase


class Neo4jExtractor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_companies(self, parse_callback):
        with self.driver.session() as session:
            session.read_transaction(
                self._read_all_company_nodes, parse_callback
            )

    @staticmethod
    def _read_all_company_nodes(tx, parse_callback):
        result = tx.run("MATCH (c:Company) RETURN c{.*}")

        for r in result:
            parse_callback(r["c"])
