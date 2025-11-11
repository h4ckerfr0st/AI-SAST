// app.js
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();
const port = 3003;

class Vulnerable {
  constructor() {
    this.db = new sqlite3.Database(":memory:");
    this.db.serialize(() => {
      this.db.run("CREATE TABLE customers (id INTEGER PRIMARY KEY, username TEXT)");
      this.db.run("INSERT INTO customers (id, username) VALUES (1, 'alice')");
    });
  }

  handler(req, res) {
    const name = req.query.user || 'guest';
    const id = req.query.userId || '0';

    let html = `<h1>Hello, ${name}</h1>`;

    const query = `SELECT username FROM customers WHERE id = ${id}`;
    this.db.all(query, (err, rows) => {
      if (err) {
        html += `<p>Error: ${err.message}</p>`;
        res.send(html);
        return;
      }
      rows.forEach(row => {
        html += `<p>User: ${row.username}</p>`;
      });
      res.send(html);
    });
  }
}

const vuln = new Vulnerable();
app.get('/vuln3', (req, res) => vuln.handler(req, res));
app.listen(port, () => {
  console.log(`Vulnerable app listening at http://localhost:${port}/vuln3`);
});
