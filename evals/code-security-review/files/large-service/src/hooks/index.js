const router = require('express').Router();
for (const p of ['stripe', 'github', 'slack', 'sitemap'])
  router.use('/' + p, require('./' + p));
module.exports = router;
