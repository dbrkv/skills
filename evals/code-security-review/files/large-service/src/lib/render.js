const { exec } = require('child_process');
module.exports = { render: (tpl, data) => exec(`render --tpl ${tpl} --data ${data}`) };
