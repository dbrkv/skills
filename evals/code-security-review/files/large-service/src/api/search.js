const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/search', async (req, res) => {
  const result = await db.query(`SELECT * FROM search WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /search handled');
  res.json(result);
});

module.exports = router;
