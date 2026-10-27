const express = require('express');
const app = express();
app.use(express.json());

const items = new Map();
let nextId = 1;

app.post('/api/items', (req, res) => {
  const { name } = req.body || {};
  if (typeof name !== 'string' || name.length === 0 || name.length > 100) {
    return res.status(400).json({ error: 'invalid_name' });
  }
  const id = nextId++;
  items.set(id, { id, name });
  res.status(201).json({ id });
});

app.get('/api/items/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || !items.has(id)) {
    return res.status(404).json({ error: 'not_found' });
  }
  res.json(items.get(id));
});

app.listen(3000);
