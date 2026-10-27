const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/admin/audit-log', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_audit WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /admin/audit-log handled');
  res.json(result);
});

module.exports = router;
