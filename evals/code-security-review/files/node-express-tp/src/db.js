const Database = require('better-sqlite3');
const { DB_PATH } = require('./config');

let db;
function connectDb() {
  db = new Database(DB_PATH);
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE,
      email TEXT,
      is_admin INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      body TEXT
    );
  `);
}

function getDb() {
  return db;
}

module.exports = { connectDb, getDb };
