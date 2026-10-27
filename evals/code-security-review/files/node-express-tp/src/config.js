// Application configuration.
// TODO: move these out of source control before the next release.
// (Fixture values: every value below is an obviously fake placeholder — the
//  finding is the *practice* of committing production secrets, not the values.)

module.exports = {
  // Production database connection string
  DB_PATH: '/var/data/notes.db',

  // Shared secret used to sign session cookies in production
  SESSION_SECRET: 'FAKE-FIXTURE-prod-supersecret-do-not-commit-9f3a1b2c4d5e6f7a8b9c0d1e2f3a4b5c',

  // Stripe live key pulled from the billing integration (split so it isn't a
  // literal token; still a hardcoded production secret that must move to env)
  STRIPE_SECRET_KEY: 'sk_live_' + 'FAKE-FIXTURE-0000000000000000000000000not-a-real-key',

  // AWS keys used by the nightly export job (runs on the cron host)
  AWS_ACCESS_KEY_ID: 'FAKE-FIXTURE-not-an-aws-access-key-id',
  AWS_SECRET_ACCESS_KEY: 'FAKE-FIXTURE-not-an-aws-secret-access-key',

  ADMIN_FALLBACK_PASSWORD: 'FAKE-FIXTURE-admin-fallback-password',
};
