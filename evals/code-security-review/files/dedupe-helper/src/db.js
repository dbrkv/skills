const Database = require('better-sqlite3');
const db = new Database('catalog.db');
db.exec('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)');
db.exec('CREATE TABLE IF NOT EXISTS admin_users (id INTEGER PRIMARY KEY, name TEXT)');
module.exports = { db };
