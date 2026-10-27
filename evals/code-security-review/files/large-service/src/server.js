const express = require('express');
const app = express();
app.use(express.json());
app.use('/api', require('./api/index'));
app.use('/admin', require('./admin/index'));
app.use('/hooks', require('./hooks/index'));
app.use('/web', require('./web/index'));
app.listen(3000);
