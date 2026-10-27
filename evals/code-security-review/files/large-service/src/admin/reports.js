const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/admin/reports', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_reports WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /admin/reports handled');
  res.json(result);
});

router.POST('/admin/reports/run', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_reports WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /admin/reports/run handled');
  res.json(result);
});

module.exports = router;
