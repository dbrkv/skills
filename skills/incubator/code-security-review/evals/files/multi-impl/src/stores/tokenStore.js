// Token storage contract. Every implementation MUST provide the same two
// operations; each platform ships its own implementation.
//
// saveToken(userId, token) -> Promise<void>
// getToken(userId)         -> Promise<string | null>

const path = require('path');

function getStore(platform) {
  if (platform === 'darwin' || platform === 'win32') {
    return require('./keychainStore');
  }
  return require('./fileStore');
}

module.exports = { getStore };
