const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/users', async (req, res) => {
  const result = await db.query(`SELECT * FROM users WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /users handled');
  res.json(result);
});

router.GET('/users/:id', async (req, res) => {
  const result = await db.query(`SELECT * FROM users WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /users/:id handled');
  res.json(result);
});

module.exports = router;
