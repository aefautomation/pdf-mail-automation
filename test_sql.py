import pyodbc

try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=AEF-IT03\\SQLEXPRESS;"
        "DATABASE=aef-test;"
        "Trusted_Connection=yes;"
    )
    print("✅ SQL connectie succesvol")
except Exception as e:
    print("❌ SQL fout:", e)
