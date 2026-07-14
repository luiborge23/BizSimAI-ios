#!/usr/bin/env python3
"""Debug: Check correct deleteContentRange field names."""

from googleapiclient.discovery import build, discovery
import json

# Get the raw discovery doc for docs API
discovery_url = "https://docs.googleapis.com/$discovery/rest?version=v1"
doc = discovery._retrieve_discovery_doc(discovery_url, 'https', None, 'googleapis.com')

schema = doc.get('schemas', {}).get('DeleteContentRangeRequest', {})
print("DeleteContentRangeRequest schema:")
print(json.dumps(schema, indent=2))

location_schema = doc.get('schemas', {}).get('Location', {})
print("\nLocation schema:")
print(json.dumps(location_schema, indent=2))

insert_schema = doc.get('schemas', {}).get('InsertTextRequest', {})
print("\nInsertTextRequest schema:")
print(json.dumps(insert_schema, indent=2))
