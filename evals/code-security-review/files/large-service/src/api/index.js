const router = require('express').Router();
for (const r of ['users', 'orders', 'products', 'search', 'cart', 'reviews', 'messages', 'uploads'])
  router.use('/' + r, require('./' + r));
module.exports = router;
