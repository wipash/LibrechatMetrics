import json
from pymongo import MongoClient
from bson import ObjectId
import os
import datetime


def get_field_type(value):
    """Helper function to get the type of a field as a string."""
    if isinstance(value, dict):
        return {k: get_field_type(v) for k, v in value.items()}
    elif isinstance(value, list):
        if value:
            # Assuming all elements in the list are of the same type
            return [get_field_type(value[0])]
        else:
            return []
    elif isinstance(value, ObjectId):
        return "ObjectId"
    elif isinstance(value, datetime.datetime):
        return "datetime"
    else:
        return type(value).__name__


def merge_schemas(schema1, schema2):
    """Recursively merge two schema definitions."""
    # If both schemas are dictionaries, merge their keys
    if isinstance(schema1, dict) and isinstance(schema2, dict):
        keys = set(schema1.keys()) | set(schema2.keys())
        merged = {}
        for key in keys:
            merged[key] = merge_schemas(schema1.get(key), schema2.get(key))
        return merged
    # If one of them is dict, and the other is not
    elif isinstance(schema1, dict):
        if schema2 is None:
            return schema1
        else:
            return [schema1, schema2]
    elif isinstance(schema2, dict):
        if schema1 is None:
            return schema2
        else:
            return [schema1, schema2]
    # If both are lists
    elif isinstance(schema1, list) and isinstance(schema2, list):
        if schema1 and schema2:
            merged_element = merge_schemas(schema1[0], schema2[0])
            return [merged_element]
        elif schema1:
            return schema1
        else:
            return schema2
    # If one is list and other is not
    elif isinstance(schema1, list):
        if schema1:
            merged_element = merge_schemas(schema1[0], schema2)
            return [merged_element]
        else:
            return [schema2]
    elif isinstance(schema2, list):
        if schema2:
            merged_element = merge_schemas(schema1, schema2[0])
            return [merged_element]
        else:
            return [schema1]
    else:
        # Both are scalar types
        if schema1 == schema2:
            return schema1
        else:
            # Return a list of possible types
            types = []
            if schema1 is not None:
                types.append(schema1)
            if schema2 is not None and schema2 not in types:
                types.append(schema2)
            if len(types) == 1:
                return types[0]
            else:
                return types


def flatten_list(lst):
    """Helper function to flatten a nested list."""
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list


def flatten_schema(schema):
    """Recursively flatten nested lists in schema."""
    if isinstance(schema, list):
        flat_list = flatten_list(schema)
        # Remove duplicates and sort
        flat_list = list(set(flat_list))
        # If only one unique element, return it without wrapping in a list
        if len(flat_list) == 1:
            return flat_list[0]
        else:
            return flat_list
    elif isinstance(schema, dict):
        return {k: flatten_schema(v) for k, v in schema.items()}
    else:
        return schema


def infer_schema(collection, sample_size=100):
    """Infer the schema of a MongoDB collection."""
    schema = {}
    cursor = collection.find().limit(sample_size)
    for document in cursor:
        document_schema = {k: get_field_type(v) for k, v in document.items()}
        schema = merge_schemas(schema, document_schema)
    # Flatten the schema to remove nested lists
    schema = flatten_schema(schema)
    return schema


def main():
    # Replace the URI with your MongoDB deployment's connection string.
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
    client = MongoClient(mongo_uri)
    db_name = "LibreChat"  # Replace with your database name
    db = client[db_name]

    # Get a list of all collections in the database
    collections = db.list_collection_names()

    database_schema = {}

    for collection_name in collections:
        print(f"Inferring schema for collection: {collection_name}")
        collection = db[collection_name]
        schema = infer_schema(collection)
        database_schema[collection_name] = schema

    # Serialize the schema to JSON
    schema_json = json.dumps(database_schema, indent=4)

    # Save the schema to a file
    with open("mongo_schema.json", "w") as f:
        f.write(schema_json)

    print("Schema has been written to mongo_schema.json")


if __name__ == "__main__":
    main()
