const express = require('express');
const { db } = require('../db');
const { searchLike } = require('../helpers/query');
const router = express.Router();

router.get('/users/search', (req, res) => {
  const term = req.query.term || '';
  res.json(searchLike(db, 'users', term));
});

module.exports = { usersRouter: router };
