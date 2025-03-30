import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


def get_all_table_names(db_path):
    """Retrieve the names of all user-defined tables in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_schema(conn, table_name):
    """Retrieve schema information for a specific table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    schema = [{"Column Name": row[1], "Data Type": row[2]} for row in cursor.fetchall()]
    return schema


def get_table_statistics(conn, table_name):
    """Compute statistics for each column in a specific table."""
    cursor = conn.cursor()
    # Get total number of rows
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    total_rows = cursor.fetchone()[0]
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cursor.fetchall()]
    
    stats = []
    for col in columns:
        # Count unique values
        cursor.execute(f"SELECT COUNT(DISTINCT \"{col}\") FROM {table_name};")
        unique_values = cursor.fetchone()[0]
        
        # Count missing values
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NULL;")
        missing_values = cursor.fetchone()[0]
        
        stats.append({
            "Column Name": col,
            "Total Rows": total_rows,
            "Unique Values": unique_values,
            "Missing Values": missing_values
        })
    return stats


def get_numerical_data(db_path):
    """
    Connects to the SQLite database and retrieves numerical columns from all tables.
    Returns a dictionary with table names as keys and DataFrames of numerical data as values.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    numerical_data = {}
    for table_name in tables:
        table = table_name[0]
        # Fetch column information
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        # Identify numerical columns
        num_cols = [col[1] for col in columns if col[2] in ('INTEGER', 'REAL')]
        if num_cols:
            # Retrieve data for numerical columns
            df = pd.read_sql_query(f"SELECT {', '.join(num_cols)} FROM {table};", conn)
            numerical_data[table] = df
    
    conn.close()
    return numerical_data


def plot_histograms(numerical_data):
    """
    Generates and displays histograms for numerical columns in each table.
    """
    for table, df in numerical_data.items():
        st.subheader(f"Table: {table}")
        for column in df.columns:
            fig, ax = plt.subplots()
            ax.hist(df[column].dropna(), bins=20, edgecolor='black')
            ax.set_title(f'Distribution of {column}')
            ax.set_xlabel(column)
            ax.set_ylabel('Frequency')
            st.pyplot(fig)


