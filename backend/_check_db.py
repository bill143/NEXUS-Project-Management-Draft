import sqlite3
conn = sqlite3.connect("openestimate.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"{len(tables)} tables")
for t in tables:
    print(f"  {t[0]}")
conn.close()
