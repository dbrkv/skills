const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// GET /products?category=<id>&min_price=<n>
// Product listing filtered by category and minimum price.
router.get('/', (req, res) => {
  const category = req.query.category;
  const minPrice = req.query.min_price;

  const db = getDb();

  // Parameters are always bound as placeholders, never interpolated.
  let query = 'SELECT id, name, price FROM products WHERE 1=1';
  const params = [];

  if (category !== undefined) {
    query += ' AND category_id = ?';
    params.push(category);
  }
  if (minPrice !== undefined) {
    query += ' AND price >= ?';
    params.push(Number(minPrice));
  }

  query += ' ORDER BY price ASC LIMIT 100';
  const rows = db.prepare(query).all(...params);
  res.json(rows);
});

module.exports = { productsRouter: router };
