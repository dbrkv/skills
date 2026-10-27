// Shared search helper used by both the public and the admin surfaces.
function searchLike(db, table, term) {
  // Table and term are interpolated; term comes straight from the query string.
  return db.prepare(`SELECT id, name FROM ${table} WHERE name LIKE '%${term}%'`).all();
}
module.exports = { searchLike };
