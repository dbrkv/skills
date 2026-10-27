const jwt = require('jsonwebtoken');
const SECRET = process.env.JWT_SECRET || 'dev-secret';
module.exports = { verify: (t) => jwt.verify(t, SECRET) };
