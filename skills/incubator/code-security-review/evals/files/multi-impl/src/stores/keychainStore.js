const keytar = require('keytar');

// macOS / Windows: OS-managed keychain.
async function saveToken(userId, token) {
  await keytar.setPassword('app', userId, token);
}

async function getToken(userId) {
  return keytar.getPassword('app', userId);
}

module.exports = { saveToken, getToken };
