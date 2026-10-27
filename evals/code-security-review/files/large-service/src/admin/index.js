const router = require('express').Router();
router.use(require('./users'));
router.use(require('./reports'));
router.use(require('./billing'));
router.use(require('./audit'));
module.exports = router;
