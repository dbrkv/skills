const express = require('express');
const app = express();
app.use(express.json());

const { adminRouter, requireAuth } = require('./routes/admin');
app.use(requireAuth);
app.use('/admin', adminRouter);

// Public read-only product catalog (no secrets, no PII).
const products = new Map();
let nextId = 1;

app.get('/api/products', (req, res) => {
  res.json([...products.values()]);
});

app.post('/api/products', (req, res) => {
  const { name, price } = req.body || {};
  if (typeof name !== 'string' || name.length === 0 || name.length > 200 ||
      !Number.isFinite(price) || price <= 0 || price > 1e6) {
    return res.status(400).json({ error: 'invalid_product' });
  }
  const id = nextId++;
  products.set(id, { id, name, price });
  res.status(201).json({ id });
});

app.listen(3000, () => console.log('catalog service listening on 3000'));
