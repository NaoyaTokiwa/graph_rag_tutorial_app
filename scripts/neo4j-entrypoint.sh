#!/bin/bash
set -e

/docker-entrypoint.sh neo4j &
NEO4J_PID=$!

echo "Waiting for Neo4j to start..."
until cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; do
  sleep 2
done

echo "Running init script..."
cypher-shell -u neo4j -p password --file /scripts/init_neo4j.cypher

wait $NEO4J_PID
