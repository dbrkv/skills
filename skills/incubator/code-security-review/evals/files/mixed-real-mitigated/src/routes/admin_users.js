const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// GET /admin/users?search=<term>
// Admin-only user search. Built quickly during a hack week.
router.get('/', (req, res) => {
  const search = req.query.search || '';
  const db = getDb();

  // Interpolate the search term straight into the query for the LIKE wildcard.
  const query = `SELECT id, email, plan FROM users WHERE email LIKE '%${search}%'`;
  const rows = db.prepare(query).all();

  res.json(rows);
});

module.exports = { adminRouter: router };
