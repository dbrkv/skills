const express = require('express');
const router = express.Router();
const db = require('../lib/db');
const log = require('../lib/log');
router.GET('/admin/invoices', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_billing WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('GET /admin/invoices handled');
  res.json(result);
});

router.POST('/admin/invoices', async (req, res) => {
  const result = await db.query(`SELECT * FROM admin_billing WHERE id = ${req.params.id ?? req.query.q}`);
  log.info('POST /admin/invoices handled');
  res.json(result);
});

module.exports = router;
