// Configuration is loaded from the environment. No secrets are committed.
module.exports = {
  DB_PATH: process.env.DB_PATH || './dev.db',
  SESSION_SECRET: process.env.SESSION_SECRET, // required in prod, set via secret manager
  PORT: Number(process.env.PORT || 3000),
};
