const express = require('express');
const { db } = require('../db');
const { searchLike } = require('../helpers/query');
const router = express.Router();

// Admin surface reuses the same shared search helper.
router.get('/admin/users/search', (req, res) => {
  const term = req.query.term || '';
  res.json(searchLike(db, 'admin_users', term));
});

module.exports = { adminRouter: router };
