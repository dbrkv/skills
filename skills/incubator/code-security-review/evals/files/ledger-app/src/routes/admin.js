const express = require('express');

const adminRouter = express.Router();
const products = new Map(); // admin-side mirror used by the delete endpoint

// Bearer-token gate: any sufficiently long token passes. There is no role model.
function requireAuth(req, res, next) {
  const token = req.headers['x-api-token'];
  if (!token || token.length < 8) {
    return res.status(401).json({ error: 'unauthenticated' });
  }
  next();
}

// Admin surface. NOTE: every authenticated user reaches this — no admin-role
// check exists anywhere in the codebase.
adminRouter.delete('/products/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || !products.has(id)) {
    return res.status(404).json({ error: 'not_found' });
  }
  products.delete(id);
  res.status(204).end();
});

adminRouter.get('/stats', (req, res) => {
  res.json({ total: products.size });
});

module.exports = { adminRouter, requireAuth, products };
