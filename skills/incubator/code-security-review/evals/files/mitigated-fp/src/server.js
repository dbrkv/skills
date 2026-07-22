const express = require('express');
const { productsRouter } = require('./routes/products');
const { searchRouter } = require('./routes/search');
const { profileRouter } = require('./routes/profile');
const { connectDb } = require('./db');

const app = express();
app.use(express.json());
app.use('/products', productsRouter);
app.use('/search', searchRouter);
app.use('/profile', profileRouter);

connectDb();
app.listen(3000, () => console.log('catalog-api on :3000'));
