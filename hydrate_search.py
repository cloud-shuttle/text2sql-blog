import psycopg2
from meilisearch import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL connection parameters
pg_host = os.getenv('PG_HOST', 'localhost')
pg_database = os.getenv('PG_DATABASE')
pg_user = os.getenv('PG_USER')
pg_password = os.getenv('PG_PASSWORD')

# Meilisearch connection parameters
meilisearch_host = os.getenv('MEILISEARCH_HOST', 'http://localhost:7700')
meilisearch_api_key = os.getenv('MEILISEARCH_API_KEY')

def get_table_columns():
    conn = psycopg2.connect(
        host=pg_host,
        port='55432',
        database=pg_database,
        user=pg_user,
        password=pg_password
    )
    cur = conn.cursor()
    
    query = """
    SELECT 
        table_name,
        array_agg(column_name || '::' || udt_name) as columns
    FROM 
        information_schema.columns
    WHERE 
        table_schema = 'public'
    GROUP BY 
        table_name
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [format_table_data(i, row) for i, row in enumerate(results)]

def format_table_data(index, row):
    table_name, columns = row
    formatted_columns = []
    for col in columns:
        name, udt_name = col.split('::', 1)
        formatted_columns.append({
            "name": name,
            "udt_name": udt_name
        })
    
    return {
        "id": index,
        "table_name": table_name,
        "columns": formatted_columns
    }

def index_in_meilisearch(data):
    client = Client(meilisearch_host, meilisearch_api_key)
    index = client.index('postgres_schema')
    
    index.add_documents(data)
    
    index.update_searchable_attributes(['table_name'])
    index.update_displayed_attributes(['table_name', 'columns'])

if __name__ == "__main__":
    table_data = get_table_columns()
    index_in_meilisearch(table_data)
    print(f"Indexed {len(table_data)} tables in Meilisearch")
