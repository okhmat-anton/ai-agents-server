#!/usr/bin/env python3
from pymongo import MongoClient

c = MongoClient("mongodb://agents:mongo_secret_2026@localhost:4717/ai_agents?authSource=admin")
db = c["ai_agents"]
print("Collections:", db.list_collection_names())

for coll_name in db.list_collection_names():
    count = db[coll_name].count_documents({})
    if count > 0:
        sample = db[coll_name].find_one()
        keys = list(sample.keys()) if sample else []
        print(f"  {coll_name}: {count} docs, keys={keys[:10]}")
