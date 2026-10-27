const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/orders', async (req, res) => {
  const result = await db.query(`SELECT * FROM orders WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /orders handled');
  res.json(result);
});

router.POST('/orders', async (req, res) => {
  const result = await db.query(`SELECT * FROM orders WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /orders handled');
  res.json(result);
});

module.exports = router;
