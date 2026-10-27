const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/messages', async (req, res) => {
  const result = await db.query(`SELECT * FROM messages WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /messages handled');
  res.json(result);
});

router.POST('/messages', async (req, res) => {
  const result = await db.query(`SELECT * FROM messages WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /messages handled');
  res.json(result);
});

module.exports = router;
