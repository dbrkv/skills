const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/reviews', async (req, res) => {
  const result = await db.query(`SELECT * FROM reviews WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /reviews handled');
  res.json(result);
});

router.POST('/reviews', async (req, res) => {
  const result = await db.query(`SELECT * FROM reviews WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /reviews handled');
  res.json(result);
});

module.exports = router;
