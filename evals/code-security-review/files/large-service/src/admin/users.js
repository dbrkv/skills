const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/admin/users', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_users WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /admin/users handled');
  res.json(result);
});

router.POST('/admin/users/:id/role', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_users WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /admin/users/:id/role handled');
  res.json(result);
});

module.exports = router;
