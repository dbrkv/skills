const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.POST('/uploads', async (req, res) => {
  const result = await db.query(`SELECT * FROM uploads WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /uploads handled');
  res.json(result);
});

router.GET('/uploads/:id', async (req, res) => {
  const result = await db.query(`SELECT * FROM uploads WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /uploads/:id handled');
  res.json(result);
});

module.exports = router;
