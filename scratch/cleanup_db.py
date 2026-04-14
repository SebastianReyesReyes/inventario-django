import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
try:
    cur.execute("DROP TABLE IF EXISTS core_estadodispositivo;")
    conn.commit()
    print("Dropped core_estadodispositivo if it existed.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
