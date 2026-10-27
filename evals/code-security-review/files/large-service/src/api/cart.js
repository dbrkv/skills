const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/cart', async (req, res) => {
  const result = await db.query(`SELECT * FROM cart WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /cart handled');
  res.json(result);
});

router.POST('/cart/checkout', async (req, res) => {
  const result = await db.query(`SELECT * FROM cart WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /cart/checkout handled');
  res.json(result);
});

module.exports = router;
