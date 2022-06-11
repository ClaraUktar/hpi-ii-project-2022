#!/bin/bash

KAFKA_CONNECT_ADDRESS=${1:-localhost}
KAFKA_CONNECT_PORT=${2:-8083}
# CORPORATE_CONFIG=${3:-"$(dirname $0)/elastic-sink-corporate.json"}
# PATENT_CONFIG=${4:-"$(dirname $0)/elastic-sink-patent.json"}
CORPORATE_CONFIG=${3:-"$(dirname $0)/neo4j-sink-announcements.json"}
PATENT_CONFIG=${4:-"$(dirname $0)/neo4j-sink-patents.json"}
KAFKA_CONNECT_API="$KAFKA_CONNECT_ADDRESS:$KAFKA_CONNECT_PORT/connectors"

# Create corporate events connector
data=$(cat $CORPORATE_CONFIG | jq -s '.[0]')
curl -X POST $KAFKA_CONNECT_API --data "$data" -H "content-type:application/json"

# Create patent events connector
data=$(cat $PATENT_CONFIG | jq -s '.[0]')
curl -X POST $KAFKA_CONNECT_API --data "$data" -H "content-type:application/json"
