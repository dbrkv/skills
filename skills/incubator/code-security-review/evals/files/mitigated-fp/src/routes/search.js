const express = require('express');
const { getDb } = require('../db');
const { validate } = require('../middleware/validate');
const router = express.Router();

const searchSchema = {
  q: { type: 'string', max: 80, pattern: /^[\w\s.-]+$/ },
};

// GET /search?q=<term>
// Full-text product search. The query string is validated and length-bounded
// before it ever touches the database, and is passed as a bound parameter.
router.get('/', (req, res) => {
  const { q } = validate(req.query, searchSchema, res);
  if (q === undefined) return; // validate already responded 400

  const db = getDb();
  const rows = db.prepare(
    'SELECT id, name FROM products WHERE name LIKE ? ESCAPE "\\" LIMIT 25'
  ).all(`%${q}%`);

  res.json(rows);
});

module.exports = { searchRouter: router };
