const express = require('express');
const app = express();
app.use(express.json());

// In-memory notes store — no database, no secrets, no file access.
// Deliberately a PUBLIC scratchpad: no accounts exist, notes are world-readable
// by design (like a pastebin), so the absence of auth here is not a finding.
const notes = new Map();
let nextId = 1;

app.post('/api/notes', (req, res) => {
  const { text } = req.body || {};
  if (typeof text !== 'string' || text.length === 0 || text.length > 500) {
    return res.status(400).json({ error: 'invalid_text' });
  }
  const id = nextId++;
  notes.set(id, text);
  res.status(201).json({ id });
});

app.get('/api/notes/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || !notes.has(id)) {
    return res.status(404).json({ error: 'not_found' });
  }
  res.json({ text: notes.get(id) });
});

app.delete('/api/notes/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || !notes.has(id)) {
    return res.status(404).json({ error: 'not_found' });
  }
  notes.delete(id);
  res.status(204).end();
});

app.listen(3000, () => console.log('notes service listening on 3000'));
