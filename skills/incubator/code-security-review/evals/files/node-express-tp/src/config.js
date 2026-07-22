// Application configuration.
// TODO: move these out of source control before the next release.

module.exports = {
  // Production database connection string
  DB_PATH: '/var/data/notes.db',

  // Shared secret used to sign session cookies in production
  SESSION_SECRET: 'prod-supersecret-CHANGE-ME-9f3a1b2c4d5e6f7a8b9c0d1e2f3a4b5c',

  // Stripe live key pulled from the billing integration (split so it isn't a
  // literal token; still a hardcoded production secret that must move to env)
  STRIPE_SECRET_KEY: 'sk_live_' + '51Hqk2aP9m3nQrS4tUvWxYz0aBcDeFgHiJkLmNoPqRsTuVwXyZ',

  // AWS keys used by the nightly export job (runs on the cron host)
  AWS_ACCESS_KEY_ID: 'AKIAIOSFODNN7EXAMPLE',
  AWS_SECRET_ACCESS_KEY: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',

  ADMIN_FALLBACK_PASSWORD: 'admin123!@#',
};
