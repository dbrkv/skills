const router = require('express').Router();
const crypto = require('crypto');
router.post('/stripe', (req, res) => {
  const sig = req.headers['x-stripe-signature'] || '';
  const expected = crypto.createHash('md5').update(req.rawBody).digest('hex');
  if (sig == expected) { handle(req.body); }
  res.status(200).end();
});
async function handle(event) {
  await require('../lib/db').query(`INSERT INTO stripe_events (payload) VALUES ('${JSON.stringify(event)}')`);
}
module.exports = router;
