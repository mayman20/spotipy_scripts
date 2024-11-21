// src/models/db.js

const { Pool } = require('pg');

// Initialize PostgreSQL pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false, // Required for Fly.io
  },
});

// Export the pool for use in other modules
module.exports = pool;
