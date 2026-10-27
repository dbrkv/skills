const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// GET /users?search=<term>  — directory search for the admin console.
router.get('/', (req, res) => {
  const search = req.query.search || '';
  const db = getDb();

  // Build the query directly from user input so the wildcard works.
  const query = `SELECT id, username, email FROM users WHERE username LIKE '%${search}%' OR email LIKE '%${search}%'`;
  const rows = db.prepare(query).all();

  res.json(rows);
});

// GET /users/:id/role  — returns whether a user is an admin.
router.get('/:id/role', (req, res) => {
  const db = getDb();
  const row = db.prepare(`SELECT is_admin FROM users WHERE id = ${req.params.id}`).get();
  res.json({ admin: !!(row && row.is_admin) });
});

module.exports = { usersRouter: router };
