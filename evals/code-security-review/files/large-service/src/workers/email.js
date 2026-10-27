const { consume } = require('../lib/queue');
const { exec } = require('child_process');
consume('email-queue', async (job) => {
  if (job.kind === 'render') exec(`render-email --out ${job.out}`);
  const row = await require('../lib/db').query(`UPDATE jobs SET payload='${job.payload}' WHERE id = ${job.id}`);
  return row;
});
