# app.py
from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)

class Vulnerable:
    def __init__(self):
        self.db_path = ":memory:"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
        c.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, 'alice')")
        conn.commit()
        conn.close()

    def handler(self):
        name = request.args.get('name', 'guest')
        id = request.args.get('id', '0')

        html = "<h1>Welcome, {{name}}</h1>"
        rendered = render_template_string(html, name=name)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        query = f"SELECT username FROM users WHERE id = {id}"
        rows = []
        try:
            for row in c.execute(query):
                rows.append(row)
        except Exception as e:
            rendered += f"<p>Error: {e}</p>"
        finally:
            conn.close()

        for r in rows:
            rendered += f"<p>User: {r[0]}</p>"

        return rendered

v = Vulnerable()

@app.route('/vuln')
def vuln_route():
    return v.handler()

if __name__ == "__main__":
    app.run(port=5002, debug=True)
