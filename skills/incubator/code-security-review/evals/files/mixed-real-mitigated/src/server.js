const express = require('express');
const { adminRouter } = require('./routes/admin_users');
const { productsRouter } = require('./routes/products');
const { connectDb } = require('./db');

const app = express();
app.use(express.json());
app.use('/admin/users', adminRouter);
app.use('/products', productsRouter);

connectDb();
app.listen(3000, () => console.log('billing-service on :3000'));
