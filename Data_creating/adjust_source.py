from pymongo import MongoClient
import re


def format_source_fields():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test']
    collection = db['news']

    # Find all documents with source field
    documents = collection.find({'source': {'$exists': True}})

    # Process each document
    for doc in documents:
        if 'source' in doc and isinstance(doc['source'], str):
            original_source = doc['source']

            # Remove "来源：" prefix
            source = original_source.replace('来源：', '')

            # Extract text before first number using regex
            match = re.search('^([^0-9]+)', source)
            if match:
                formatted_source = match.group(1).strip()

                # Update the document only if the source was modified
                if formatted_source != original_source:
                    collection.update_one(
                        {'_id': doc['_id']},
                        {'$set': {'source': formatted_source}}
                    )

    client.close()


if __name__ == "__main__":
    try:
        format_source_fields()
        print("Source fields have been successfully formatted.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")