import sys
from meilisearch import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Meilisearch connection parameters
meilisearch_host = os.getenv('MEILISEARCH_HOST', 'http://localhost:7700')
meilisearch_api_key = os.getenv('MEILISEARCH_API_KEY')

def search_table(query):
    client = Client(meilisearch_host, meilisearch_api_key)
    index = client.index('postgres_schema')
    
    results = index.search(query)
    
    if results['hits']:
        first_hit = results['hits'][0]
        return generate_create_table_statement(first_hit)
    else:
        return f"No tables found matching '{query}'"

def generate_create_table_statement(table_info):
    table_name = table_info['table_name']
    columns = table_info['columns']
    
    column_definitions = []
    for column in columns:
        column_name = column['name']
        data_type = column['udt_name']
        column_definitions.append(f"    {column_name} {data_type}")
    
    column_string = ',\n'.join(column_definitions)
    
    create_table_statement = f"""CREATE TABLE {table_name} (
{column_string}
);"""
    
    return create_table_statement

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query_table.py <table_name>")
        sys.exit(1)
    
    table_name = sys.argv[1]
    result = search_table(table_name)
    print(result)
