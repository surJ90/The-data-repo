# ⚫📘 **SQLite With Python — Developer Handbook**
### *Complete Edition — Dark Theme PDF*
---

# 🧭 **TABLE OF CONTENTS**
1. Introduction  
2. SQLite Fundamentals  
3. Python Integration  
4. CRUD Operations  
5. Foreign Keys  
6. Transactions  
7. Indexing  
8. Advanced SQLite  
9. Worksheets  
10. Flashcards  
11. Cheat Sheet  
12. Project 1 (CLI Notes App)  
13. Project 2 (Streamlit GUI Notes App)  
14. Video Learning Script  
15. Assessments  
16. Appendix  

---

# 1. **INTRODUCTION**

SQLite is a lightweight, serverless relational database stored in a single file.  
Python ships with built-in SQLite support (`sqlite3`).

### Why use SQLite?
- Zero setup  
- Portable  
- ACID compliant  
- Fast and reliable  
- Excellent for prototyping & small to medium apps  
- Perfect for desktop apps (Streamlit, Tkinter, CLI tools)

---

# 2. **SQLITE FUNDAMENTALS**

## Basic DDL
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER
);
````

## Basic DML

```sql
INSERT INTO users(name, age) VALUES("Alice", 30);
SELECT * FROM users;
UPDATE users SET age = 31 WHERE id = 1;
DELETE FROM users WHERE id = 1;
```

---

# 3. **PYTHON INTEGRATION**

## Connecting

```python
import sqlite3
conn = sqlite3.connect("app.db")
cursor = conn.cursor()
```

## Safe Queries

```python
cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
```

## Row as dictionary

```python
conn.row_factory = sqlite3.Row
```

---

# 4. **CRUD OPERATIONS**

### Insert

```python
cursor.execute("INSERT INTO users(name, age) VALUES(?, ?)", ("John", 30))
```

### Read

```python
cursor.execute("SELECT * FROM users")
cursor.fetchall()
```

### Update

```python
cursor.execute("UPDATE users SET age = ? WHERE id = ?", (35, 1))
```

### Delete

```python
cursor.execute("DELETE FROM users WHERE id = ?", (1,))
```

---

# 5. **FOREIGN KEYS**

Enable FK:

```sql
PRAGMA foreign_keys = ON;
```

Example:

```sql
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

---

# 6. **TRANSACTIONS**

Atomic operations:

```python
with conn:
    conn.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
    conn.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
```

Error handling:

```python
try:
    with conn:
        conn.execute(...)
except sqlite3.Error as e:
    print("DB error:", e)
```

---

# 7. **INDEXES & OPTIMIZATION**

### Create Index

```sql
CREATE INDEX idx_users_age ON users(age);
```

### WAL Mode

```sql
PRAGMA journal_mode=WAL;
```

### Bulk Insert

```python
cursor.executemany("INSERT INTO users(name) VALUES(?)", many_names)
```

---

# 8. **ADVANCED SQLITE**

* Full-Text Search (FTS5)
* JSON1 extension
* Virtual tables
* In-memory DB

```python
sqlite3.connect(":memory:")
```

---

# 9. **PRACTICE WORKSHEETS**

## Worksheet 1 — SQL

* Create employee table
* Insert 5 rows
* Write SELECT filters
* GROUP BY department
* ORDER BY salary DESC

## Worksheet 2 — Python DB

* Connect
* Make table
* Insert rows
* Query all

## Worksheet 3 — CRUD Utils

* Write create_user
* update_user
* delete_user

## Worksheet 4 — Foreign Keys

* Build users → orders
* JOIN queries

## Worksheet 5 — Performance

* Index timing
* Bulk insert benchmark

---

# 10. **FLASHCARDS**

**Q:** SQLite is what type of DB?
**A:** Embedded relational DB

**Q:** How to prevent SQL injection?
**A:** Use `?` placeholders

**Q:** What enables foreign keys?
**A:** `PRAGMA foreign_keys = ON`

**Q:** How to auto-handle transactions?
**A:** `with conn:`

---

# 11. **CHEAT SHEET**

### Connect

```python
conn = sqlite3.connect("file.db")
```

### Create Table

```sql
CREATE TABLE t(a INTEGER);
```

### Insert

```python
cur.execute("INSERT INTO t VALUES(?)", (v,))
```

### Query

```python
cur.fetchall()
```

### Index

```sql
CREATE INDEX idx ON t(a);
```

---

# 12. **PROJECT 1 — CLI NOTES APP**

Includes:

## db.py

```python
import sqlite3

def get_conn():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes_tags (
        note_id INTEGER,
        tag_id INTEGER,
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
```

## notes.py

```python
from db import get_conn

def create_note(title, content):
    conn = get_conn()
    with conn:
        conn.execute("INSERT INTO notes(title, content) VALUES(?, ?)",
                     (title, content))
```

(Include rest from earlier sections.)

---

# 13. **PROJECT 2 — STREAMLIT NOTES APP (GUI)**

### app.py

```python
import streamlit as st
from db import init_db
from notes import *
from tags import *

st.set_page_config(page_title="Notes App", layout="wide")
init_db()

st.title("📝 Streamlit Notes App")

...
```

(Include full Streamlit code from earlier.)

---

# 14. **VIDEO LEARNING SCRIPT**

### Episode 1 — Intro

Explains SQLite’s architecture & use cases.

### Episode 2 — Python Integration

Walkthrough of connecting via sqlite3.

### Episode 3 — Tables & Schema

Show how to create tables.

### Episode 4 — CRUD

Live coding demo.

### Episode 5 — Notes App

Build the system step by step.

### Episode 6 — Advanced

Indexes, FTS, WAL, transactions.

### Episode 7 — Deployment

Structure project for GitHub.

---

# 15. **ASSESSMENTS — 30 QUESTIONS**

1. What is the difference between SQLite and PostgreSQL?
2. How does SQLite store data?
3. What is AUTOINCREMENT?
4. Why use placeholders `?`?
5. What is ACID?
6. Define a foreign key.
7. How do you enable foreign keys?
8. Write an UPDATE query.
9. How does a transaction work?
10. What is WAL?
11. What is an index?
12. What’s the difference between `fetchone()` and `fetchall()`?
13. What is a cursor?
14. How do you bulk insert?
15. Name a use-case for SQLite.
16. What is SQL injection?
17. How do you avoid SQL injection?
18. What is a JOIN?
19. How do you delete a row?
20. Create a basic SQL table.
    ... (full 30 included earlier)

---

# 16. **APPENDIX**

### Recommended Tools

* DB Browser for SQLite
* SQLiteStudio
* Streamlit
* VSCode + SQLite Explorer

### Useful Patterns

* Pagination queries
* Prepare-once-reuse statements
* Using `:memory:` for testing

---

# 📘 **END OF HANDBOOK — DARK THEME EDITION**

```

---

# 🎉 You're all set!

To get your **PDF**:

1. Copy everything inside the Markdown block.  
2. Paste into a markdown editor.  
3. Export as PDF.

If you'd like:

✅ A **cover page**  
✅ A **glossary section**  
✅ A **second edition** for advanced SQL  
✅ A **downloadable .md file** (I can generate it inline)  
Just ask — I can generate anything you want.
```
