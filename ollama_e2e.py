import sys
import os
from dotenv import load_dotenv
import ollama
from meilisearch import Client

# Load environment variables
load_dotenv()

# Meilisearch connection parameters
meilisearch_host = os.getenv('MEILISEARCH_HOST', 'http://localhost:7700')
meilisearch_api_key = os.getenv('MEILISEARCH_API_KEY')

def get_table_schema(table_name):
    client = Client(meilisearch_host, meilisearch_api_key)
    index = client.index('postgres_schema')
    
    results = index.search(table_name)
    
    if results['hits']:
        first_hit = results['hits'][0]
        return generate_create_table_statement(first_hit)
    else:
        return None

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

def generate_sql(table_name, query):
    schema = get_table_schema(table_name)
    if not schema:
        return f"No table found matching '{table_name}'"

    system_prompt = f"Here is the database schema that the SQL query will run on:\n{schema}"
    
    try:
        r = ollama.generate(
            model='duckdb-nsql',
            system=system_prompt,
            prompt=query,
        )
        return r['response']
    except Exception as e:
        return f"Error generating SQL: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python meilisearch_ollama_sql.py <table_name> <query>")
        sys.exit(1)
    
    table_name = sys.argv[1]
    query = sys.argv[2]
    
    result = generate_sql(table_name, query)
    print(result)
