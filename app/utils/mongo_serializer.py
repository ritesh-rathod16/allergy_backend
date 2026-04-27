from bson import ObjectId

def serialize_mongo(doc):
    if not doc:
        return doc
    
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Also handle nested objects if necessary, though a simple top-level _id is usually the main culprit
    return doc

def serialize_list(docs):
    return [serialize_mongo(doc) for doc in docs]
