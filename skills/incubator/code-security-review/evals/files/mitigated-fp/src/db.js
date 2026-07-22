const Database = require('better-sqlite3');
const { DB_PATH } = require('./config');

let db;
function connectDb() {
  db = new Database(DB_PATH);
  db.exec(`
    CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL, category_id INTEGER);
    CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, bio TEXT);
  `);
}
function getDb() { return db; }
module.exports = { connectDb, getDb };
