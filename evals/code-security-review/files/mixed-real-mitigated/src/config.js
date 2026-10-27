module.exports = {
  DB_PATH: process.env.DB_PATH || './billing.db',
  PORT: Number(process.env.PORT || 3000),
};
