import streamlit as st
import sqlite3
from utils.llm_wrapper import generate_sql_from_nl
from utils.get_db_info import get_all_table_names, get_table_schema, get_table_statistics, plot_histograms, get_numerical_data
import pandas as pd

# Initialize query history in session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []

# Initialise default tab
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Overview"

# Initialize session state
if 'user_query' not in st.session_state:
    st.session_state.user_query = ""
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ""
if 'query_results' not in st.session_state:
    st.session_state.query_results = None
if 'refine_query' not in st.session_state:
    st.session_state.refine_query = False
if 'last_action' not in st.session_state:
    st.session_state.last_action = ""  # can be 'initial' or 'refined'

def activate_refinement():
    st.session_state.refine_query = True

def reset_query():
    st.session_state.user_query = ""
    st.session_state.sql_query = ""
    st.session_state.query_results = None
    st.session_state.refine_query = False
    st.session_state.last_action = ""
    st.session_state.active_tab = "Query"
    st.rerun()

def update_query_history(sql_query, table_name, df, from_refinement=False):
    if st.session_state.query_history:
        # Always update the most recent entry if it's the same table
        last_item = st.session_state.query_history[-1]
        if last_item['table'] == table_name:
            last_item['query'] = sql_query
            last_item['results'] = df
            return

    # Only append if this is a new table or nothing to update
    st.session_state.query_history.append({
        'query': sql_query,
        'table': table_name,
        'results': df
    })

    # Keep last 10 results
    st.session_state.query_history = st.session_state.query_history[-10:]



# Formatting sidebar
st.markdown("""
    <style>
        /* Increase sidebar width */
        section[data-testid="stSidebar"] {
            width: 525px !important;       /* Controls the sidebar container */
        }
        section[data-testid="stSidebar"] > div:first-child {
            width: 520px !important;       /* Controls the inner block */
        }

        /* Make sidebar font bigger */
        .css-1d391kg, .css-1v0mbdj, .css-1cypcdb {
            font-size: 18px !important;
        }

        /* Add padding inside the sidebar */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
            padding-left: 1.5rem;
        }

        /* Optional: bold the active tab */
        label[data-baseweb="radio"] > div {
            padding: 6px 10px;
            border-radius: 5px;
        }

        /* Hover effect on sidebar radio items */
        label[data-baseweb="radio"]:hover {
            background-color: #333333;
        }

        /* Highlight selected radio item */
        input[type="radio"]:checked + div {
            background-color: #ff4b4b33;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)



# Tabs for "Query" and "History"
tab = st.sidebar.radio("Navigation", ["Overview", "Query", "History"], key="active_tab")

# Adding user guide
with st.sidebar.expander("User Guide", expanded=False):
    st.markdown("""
    ### How to Use This App

    **1. Overview Tab**
    - View the structure of the dataset.
    - See column names, data types, missing values, and distributions.

    **2. Query Tab**
    - Type natural language questions (e.g., *"show all orders from Germany"*).
    - Does not allow to modify the original data in any form (upadate, delete, insert, etc.)
    - View the generated SQL and table output.
    - Download the result or refine your query without retyping.
    
    **Refining Queries**
    - Use the *"Refine"* button to tweak your query (e.g., *"only include orders above quantity 10"*).
    - The app remembers your context and updates the result.

    **Reset**
    - Use the *Reset Query* button to start fresh.

    **Downloading**
    - If you're happy with the result, click *Download CSV* to save it locally.

    **3. History Tab**
    - Browse the last 10 queries and their results.
    """)


#------------------------------------------------------------------
# TAB 1: Overview Tab
#------------------------------------------------------------------

# Path to your SQLite database
db_path = "db/prototype.db"

# Retrieve all table names
table_names = get_all_table_names(db_path)
if tab == "Overview":
    # Streamlit UI
    st.title("Database Overview")

    # Display information for each table
    conn = sqlite3.connect(db_path)
    for table in table_names:
        st.header(f"Table: {table}")
        
        # Display schema information
        schema = get_table_schema(conn, table)
        df_schema = pd.DataFrame(schema)
        st.subheader(f"{table} Schema Information")
        st.dataframe(df_schema, use_container_width=True)
        
        # Display statistics
        stats = get_table_statistics(conn, table)
        df_stats = pd.DataFrame(stats)
        st.subheader(f"{table} Table Statistics")
        st.dataframe(df_stats, use_container_width=True)

    # Show distributions of numerical features
    numerical_data = get_numerical_data(db_path)
    st.header("Distribution of Numerical Features")
    if numerical_data:
        plot_histograms(numerical_data)
    else:
        st.info("No numerical data found in the database.")

    conn.close()

#------------------------------------------------------------------
# TAB 2: Querying
#------------------------------------------------------------------

elif tab == "Query":
    st.title("Natural Language to SQL Processor")
    st.header("Query the Database")

    user_question = st.text_input("Ask your question about the data:", value=st.session_state.user_query)

    # Initial query logic
    if st.button("Run Query") and user_question and st.session_state.last_action == "":
        with st.spinner("Generating SQL and fetching results..."):
            try:
                sql_query, table_name = generate_sql_from_nl(user_question)
                if not sql_query:
                    st.warning("The model did not return any SQL.")
                else:
                    st.session_state.user_query = user_question
                    st.session_state.sql_query = sql_query
                    conn = sqlite3.connect("db/prototype.db")
                    df = pd.read_sql_query(sql_query, conn)
                    conn.close()
                    st.session_state.query_results = df
                    update_query_history(sql_query, table_name, df)
                    st.session_state.last_action = "initial"
                    st.rerun()
            except Exception as e:
                st.error("Failed to process your question.")
                st.exception(e)

    # Refinement interface
    if st.session_state.refine_query:
        st.markdown("### Refine Your Query")
        refinement = st.text_area("Specify how you'd like to refine the query:", height=100)
        if st.button("Submit Refinement"):
            if refinement:
                refined_prompt = f"Original query: {st.session_state.user_query}. Refinement: {refinement}"
                with st.spinner("Generating SQL and fetching results..."):
                    try:
                        sql_query, table_name = generate_sql_from_nl(refined_prompt)
                        if not sql_query:
                            st.warning("The model did not return any SQL.")
                        else:
                            st.session_state.sql_query = sql_query
                            conn = sqlite3.connect("db/prototype.db")
                            df = pd.read_sql_query(sql_query, conn)
                            conn.close()
                            st.session_state.query_results = df
                            update_query_history(sql_query, table_name, df)
                            st.session_state.refine_query = False
                            st.session_state.last_action = "refined"
                            st.rerun()
                    except Exception as e:
                        st.error("Failed to refine your query.")
                        st.exception(e)
            else:
                st.warning("Please describe your refinement.")

    # Always display current SQL query if available
    if st.session_state.sql_query:
        st.markdown("### Generated SQL Query")
        st.code(st.session_state.sql_query, language="sql")

    # Always display results if available
    if st.session_state.query_results is not None:
        st.markdown("### Query Results")
        st.dataframe(st.session_state.query_results, use_container_width=True)

        st.markdown("### Are you satisfied with the query results?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, download results"):
                csv = st.session_state.query_results.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "query_results.csv", "text/csv")
        with col2:
            st.button("No, refine the query", on_click=activate_refinement)
    st.markdown("---")
    st.button("Reset Query", on_click=reset_query)

#------------------------------------------------------------------
# TAB 3: History
#------------------------------------------------------------------
elif tab == "History":
    st.title("Query History (Last 10)")

    if not st.session_state.query_history:
        st.info("No query history yet.")
    else:
        for i, item in enumerate((st.session_state.query_history), 1):
            with st.expander(f"Query {i}: {item['table'] or 'Unknown Table'}"):
                st.code(item['query'], language='sql')
                st.dataframe(item['results'], use_container_width=True)
