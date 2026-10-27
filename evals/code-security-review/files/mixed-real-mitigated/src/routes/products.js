const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// GET /products?category=<id>
// Product listing. Uses a bound parameter for the category filter.
router.get('/', (req, res) => {
  const category = req.query.category;
  const db = getDb();

  let query = 'SELECT id, name, price FROM products WHERE 1=1';
  const params = [];
  if (category !== undefined) {
    query += ' AND category_id = ?';
    params.push(category);
  }
  query += ' ORDER BY price ASC LIMIT 100';

  const rows = db.prepare(query).all(...params);
  res.json(rows);
});

module.exports = { productsRouter: router };
