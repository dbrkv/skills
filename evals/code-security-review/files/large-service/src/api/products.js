const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/products', async (req, res) => {
  const result = await db.query(`SELECT * FROM products WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /products handled');
  res.json(result);
});

router.GET('/products/:id', async (req, res) => {
  const result = await db.query(`SELECT * FROM products WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /products/:id handled');
  res.json(result);
});

module.exports = router;
