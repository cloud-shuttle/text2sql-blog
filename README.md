
Hey folks, we are going to build out a text2sql solution. To do that first up we need to install ollama and download the duckdb-nsql 7b parameter LLM.

<!-- this is the embedded video minus this comment -->

<div style="position: relative; width: 100%; padding-bottom: 56.25%">
<iframe src="https://youtu.be/XDktyydC3hQ" 
        title="Text2SQL Demo and Blog" frameborder="0" allowfullscreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        style="position: absolute; width: 100%; height: 100%;">
</iframe>
</div>

<!-- end embedded video -->


Go to https://ollama.com/ and download the binary (going to assume you're on a mac for this blog)

```bash
ollama run duckdb-nsql
```

## Part 2: Ask a question of duckdb-nsql LLM

First up we want to check the response from the duckdb-nsql LLM with no context
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "duckdb-nsql",
  "prompt": "The total number of sales for APAC this year",
  "stream": false
}'
```

Okay that returns a response, let's use jq to make that legible
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "duckdb-nsql",
  "prompt": "The total number of sales for APAC this year",
  "stream": false
}' | jq '.response'
```

Okay that looks like sql but we haven't even got a database yet so the LLM has basically guessed the answer. Let's get to work on spinning up a database.

## Part 3: Spin up Northwind database locally

Yes the blast from the past. Let's spin up Northwind but this time let's do it using PostgreSQL. Luckily I found this repo on Github by a chap by the name Pascal Thomas (please give him a star for his awesome work when you visit): https://github.com/pthom/northwind_psql

This has a docker compose with both postgres database, pgAdmin and a bootstrap script to load in the Northwind database. Let's go ahead and clone it and spin it up:

```bash
git clone git@github.com:pthom/northwind_psql.git
cd northwind_psql
docker-compose up
```

No that it has spun up, let's go to the browser at http://localhost:5050/ and login to pgAdmin with the following credentials (let's not do this in prod, folks!):
- General Tab:
    - Name = db
- Connection Tab:
    - Host name: db
    - Username: postgres
    - Password: postgres

## Part 4: Take a look at the information schema

In there, let's take a look at a few tables and then look at the information schema with this simple query:
```sql
select * from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;
```

As you can see we've got a bunch of information in regards to the tables in postgres loaded from the Northwind database. We can use this information to form the basis of our Prompt engineering. In other words, to ground our prompt with some context about the types of tables and columns available in the database.

## Part 5: Spin up Meilisearch as our RAG

Okay so let's spin up Meilisearch, a rust based search database that we can use to store the table and column information that we can use as a RAG for the LLM.

```bash
docker pull getmeili/meilisearch:v1.10

docker run -it --rm \
  -p 7700:7700 \
  -v $(pwd)/meili_data:/meili_data \
  getmeili/meilisearch:v1.10
```

Now that this service is up, let's go ahead and get some data in there!

## Part 6: Python scripts

First up we need to load some data in from the PostgreSQL information schema into Meilisearch so let's clone my repo and get a python environment setup and clone the repo with the code in it.

```shell
git clone git@github.com:cloud-shuttle/text2sql-blog.git
cd text2sql-blog
uv venv
source .venv/bin/activate
uv pip install psycopg2-binary python-dotenv meilisearch ollama
```

Then copy the below into your dot env (.env) file (again this is for local testing only and not for prod use cases)

```bash
PG_HOST="localhost"
PG_DATABASE="northwind"
PG_USER="postgres"
PG_PASSWORD="postgres"

# Meilisearch connection parameters
MEILISEARCH_HOST="http://localhost:7700"
MEILISEARCH_API_KEY="ADSF"
```

Now onto the fun part.

### Hydrate Meilisearch

Now we want to load up the metadata from the information schema in PostgreSQL into Meilisearch
```bash
python hydrate_search.py
Indexed 14 tables in Meilisearch
```

### Query Meilisearch to sample the results

Next we want to query Meilisearch to sample the results

```bash
python search_results.py orders
CREATE TABLE orders (
    order_id int2,
    employee_id int2,
    order_date date,
    required_date date,
    shipped_date date,
    ship_via int2,
    freight float4,
    customer_id varchar,
    ship_name varchar,
    ship_address varchar,
    ship_city varchar,
    ship_region varchar,
    ship_postal_code varchar,
    ship_country varchar
);
```

### Use the context to prompt Ollama

Now that we have the context from our search database RAG, we can use it as part of our prompt to the duckdb-nsql model in Ollama to get our text2sql result.

```bash
python ollama_e2e.py orders "the total number of orders from Belgium in 1996"
SELECT COUNT(*) FROM orders WHERE ship_country = 'Belgium' AND order_date BETWEEN '1996-01-01' AND '1996-12-31';
```

Now let's go ahead and use the outputted query in PGAdmin to see if it works?

```sql
SELECT COUNT(*) FROM orders WHERE ship_country = 'Belgium' AND order_date BETWEEN '1996-01-01' AND '1996-12-31';
--result 2
```

Awesome so it works for this one use case and obviously productionising this and going through the edge case would be some work but I thought, it's Sunday, let's have some fun.
