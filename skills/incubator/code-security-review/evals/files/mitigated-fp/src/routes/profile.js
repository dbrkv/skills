const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// GET /profile/:username
// Renders a user's public profile. The username comes from the database, but
// we render it through a templating engine that HTML-escapes by default, so
// stored content can never break out into markup.
router.get('/:username', (req, res) => {
  const db = getDb();
  const row = db.prepare('SELECT username, bio FROM profiles WHERE username = ?').get(req.params.username);

  if (!row) return res.status(404).send('not found');

  // `escapeHtml` is applied to any user-controlled field before interpolation.
  res.type('html').send(renderProfile(row));
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderProfile(row) {
  return `<!doctype html>
<html><body>
  <h1>${escapeHtml(row.username)}</h1>
  <p>${escapeHtml(row.bio)}</p>
</body></html>`;
}

module.exports = { profileRouter: router };
