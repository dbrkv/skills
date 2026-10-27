const fs = require('fs');
const os = require('os');
const path = require('path');

const TOKENS_FILE = path.join(os.homedir(), '.app', 'tokens.json');

// Linux: plain file in the user's home directory.
async function saveToken(userId, token) {
  const tokens = fs.existsSync(TOKENS_FILE) ? JSON.parse(fs.readFileSync(TOKENS_FILE, 'utf8')) : {};
  tokens[userId] = token;
  fs.writeFileSync(TOKENS_FILE, JSON.stringify(tokens, null, 2));
}

async function getToken(userId) {
  if (!fs.existsSync(TOKENS_FILE)) return null;
  const tokens = JSON.parse(fs.readFileSync(TOKENS_FILE, 'utf8'));
  return tokens[userId] || null;
}

module.exports = { saveToken, getToken };
