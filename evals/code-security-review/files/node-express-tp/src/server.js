const express = require('express');
const { usersRouter } = require('./routes/users');
const { notesRouter } = require('./routes/notes');
const { connectDb } = require('./db');

const app = express();
app.use(express.json());

app.use('/users', usersRouter);
app.use('/notes', notesRouter);

connectDb();

app.listen(3000, () => console.log('API listening on :3000'));
