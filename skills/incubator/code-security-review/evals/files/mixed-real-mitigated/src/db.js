const Database = require('better-sqlite3');
const { DB_PATH } = require('./config');
let db;
function connectDb() {
  db = new Database(DB_PATH);
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, plan TEXT);
    CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL);
  `);
}
function getDb() { return db; }
module.exports = { connectDb, getDb };
