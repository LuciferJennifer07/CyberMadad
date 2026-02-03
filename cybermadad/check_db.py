import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("SELECT id, allow_contact FROM cases ORDER BY id DESC")
rows = c.fetchall()

print("Case ID | allow_contact")
print("------------------------")
for r in rows:
    print(r[0], " | ", r[1])

conn.close()
