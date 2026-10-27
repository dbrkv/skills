const express = require('express');
const { Pool } = require('pg');
const Stripe = require('stripe');
const jwt = require('jsonwebtoken');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
const JWT_SECRET = process.env.JWT_SECRET;

const upload = multer({ dest: '/tmp/uploads' });

// Authenticate bearer tokens issued at login.
function auth(req, res, next) {
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (e) {
    res.status(401).json({ error: 'unauthorized' });
  }
}

// POST /orders — create an order and charge the customer's card.
app.post('/orders', auth, async (req, res) => {
  const { items, shipping_address } = req.body;
  const amount = items.reduce((s, i) => s + i.price * i.qty, 0);

  const charge = await stripe.paymentIntents.create({
    amount: Math.round(amount * 100),
    currency: 'usd',
    customer: req.user.stripe_customer_id,
  });

  const result = await pool.query(
    'INSERT INTO orders (user_id, total, shipping_address, stripe_id) VALUES ($1, $2, $3, $4) RETURNING id',
    [req.user.id, amount, JSON.stringify(shipping_address), charge.id]
  );

  res.json({ order_id: result.rows[0].id });
});

// POST /orders/:id/receipt — upload a scanned paper receipt image.
app.post('/orders/:id/receipt', auth, upload.single('receipt'), async (req, res) => {
  const orderId = req.params.id;
  const dest = path.join('/var/receipts', orderId, req.file.originalname);
  fs.copyFileSync(req.file.path, dest);
  await pool.query('UPDATE orders SET receipt_path = $1 WHERE id = $2', [dest, orderId]);
  res.json({ ok: true });
});

// GET /orders/:id/track — look up tracking info for a guest from a signed link.
app.get('/orders/:id/track', async (req, res) => {
  const id = req.params.id;
  const token = req.query.token;
  const row = await pool.query('SELECT tracking FROM orders WHERE id = $1 AND track_token = $2', [id, token]);
  res.json({ tracking: row.rows[0]?.tracking });
});

app.listen(3000, () => console.log('order-service on :3000'));
