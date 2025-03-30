# utils/llm_wrapper.py
import cohere
import json
import sqlparse

# Load the API key from file
with open("secrets/api_key.txt", "r") as f:
    COHERE_API_KEY = f.read().strip()

# Initialize client
co = cohere.ClientV2(COHERE_API_KEY)

system_prompt = {
    'role': 'system',
    'content': """
    You are an expert data analyst who writes clean, executable SQLite queries based on a given database schema and user request. Additionally, identify the primary table involved in the query.

    ## Rules:
    - Respond with a JSON object containing two keys:
      - "sql_query": the valid SQL query as a string
      - "table_name": an appropiate name for a table of results based on the user query as a string. Capitalise the first letter of each word and use spaces
    - Do NOT include any commentary or explanations
    - Use only the tables and columns defined in the schema
    - Only use SELECT queries — never write INSERT, UPDATE, DELETE, DROP, etc.
    - Use double quotes for table and column names if needed

    ## Database schema:
    CREATE TABLE IF NOT EXISTS "orders" (
        "InvoiceNo" TEXT,
        "StockCode" TEXT,
        "Description" TEXT,
        "Quantity" INTEGER,
        "InvoiceDate" TIMESTAMP,
        "UnitPrice" REAL,
        "CustomerID" REAL,
        "Country" TEXT
    );
    """
}

def generate_sql_from_nl(user_query: str):
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            system_prompt,
            {
                'role': 'user',
                'content': user_query
            }
        ],
        response_format={"type": "json_object"}  # Ensure the response is in JSON format
    )

    response_content = response.message.content[0].text.strip()

    try:
        response_json = json.loads(response_content)
        sql_query = response_json.get("sql_query", "")
        table_name = response_json.get("table_name", "")
        if sql_query:
            sql_query = sqlparse.format(sql_query, reindent=True, keyword_case='upper')
    except json.JSONDecodeError:
        sql_query = ""
        table_name = ""

    return sql_query, table_name
