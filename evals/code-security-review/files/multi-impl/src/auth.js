const os = require('os');
const express = require('express');
const { getStore } = require('./stores/tokenStore');

const app = express();
app.use(express.json());
const store = getStore(os.platform());

app.post('/login', async (req, res) => {
  const { userId, token } = req.body || {};
  if (!userId || !token) return res.status(400).json({ error: 'bad_request' });
  await store.saveToken(userId, token);
  res.status(204).end();
});

app.get('/session', async (req, res) => {
  const token = await store.getToken(req.query.userId);
  if (!token) return res.status(404).json({ error: 'no_session' });
  res.json({ ok: true });
});

app.listen(3000);
