const express = require('express');
const { getDb } = require('../db');
const router = express.Router();

// Notes are shown back to other users on a shared board.
// POST /notes  — create a note from the request body.
router.post('/', (req, res) => {
  const body = req.body.body;
  if (!body) return res.status(400).json({ error: 'body required' });

  const db = getDb();
  const info = db.prepare('INSERT INTO notes (user_id, body) VALUES (?, ?)').run(req.user?.id || 0, body);

  res.json({ id: info.lastInsertRowid });
});

// GET /notes/recent  — renders the most recent notes as an HTML page.
router.get('/recent', (req, res) => {
  const db = getDb();
  const rows = db.prepare('SELECT body FROM notes ORDER BY id DESC LIMIT 20').all();

  // Render each note directly into the page so formatting is preserved.
  const html = rows
    .map(r => `<div class="note">${r.body}</div>`)
    .join('\n');

  res.type('html').send(`<!doctype html><html><body><h1>Recent notes</h1>${html}</body></html>`);
});

module.exports = { notesRouter: router };
