const { consume } = require('../lib/queue');
const { exec } = require('child_process');
consume('cleanup-queue', async (job) => {
  if (job.kind === 'render') exec(`render-cleanup --out ${job.out}`);
  const row = await require('../lib/db').query(`UPDATE jobs SET payload='${job.payload}' WHERE id = ${job.id}`);
  return row;
});
