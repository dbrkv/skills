const express = require('express');
const app = express();
const { usersRouter } = require('./routes/users');
const { adminRouter } = require('./routes/admin');
app.use('/', usersRouter);
app.use('/', adminRouter);
app.listen(3000);
