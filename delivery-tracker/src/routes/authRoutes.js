// src/routes/authRoutes.js

const express = require('express');
const { body, validationResult } = require('express-validator');
const bcrypt = require('bcrypt');
const router = express.Router();
const pool = require('../models/db');

// User Registration
router.post('/register', [
  body('username')
    .isAlphanumeric().withMessage('Username must be alphanumeric.')
    .isLength({ min: 3, max: 50 }).withMessage('Username must be between 3 and 50 characters.'),
  body('password')
    .isLength({ min: 6 }).withMessage('Password must be at least 6 characters long.'),
  body('role')
    .isIn(['driver', 'cashier']).withMessage('Invalid role.')
], async (req, res) => {
  // Validate Inputs
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    console.error('Registration Validation Errors:', errors.array());
    return res.status(400).json({ errors: errors.array() });
  }
  
  const { username, password, role } = req.body;
  
  try {
    // Check if username already exists
    const userCheck = await pool.query('SELECT * FROM users WHERE username = $1', [username]);
    if (userCheck.rows.length > 0) {
      return res.status(409).send('Username already exists.');
    }

    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10);
    
    // Insert the new user
    const insertQuery = 'INSERT INTO users (username, password, role) VALUES ($1, $2, $3)';
    await pool.query(insertQuery, [username, hashedPassword, role]);
    
    console.log(`New user registered: ${username} as ${role}`);
    res.status(201).send('User registered successfully.');
  } catch (err) {
    console.error('Error during user registration:', err);
    res.status(500).send('Error registering user.');
  }
});

// User Login
router.post('/login', [
  body('username')
    .notEmpty().withMessage('Username is required.')
    .isAlphanumeric().withMessage('Username must be alphanumeric.'),
  body('password')
    .notEmpty().withMessage('Password is required.')
], async (req, res) => {
  // Validate Inputs
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    console.error('Login Validation Errors:', errors.array());
    return res.status(400).json({ errors: errors.array() });
  }
  
  const { username, password } = req.body;
  
  try {
    // Retrieve user from the database
    const selectQuery = 'SELECT * FROM users WHERE username = $1';
    const result = await pool.query(selectQuery, [username]);
    
    if (result.rows.length === 0) {
      console.warn(`Login attempt with invalid username: ${username}`);
      return res.status(401).send('Invalid credentials.');
    }
    
    const user = result.rows[0];
    
    // Compare hashed passwords
    const isMatch = await bcrypt.compare(password, user.password);
    
    if (!isMatch) {
      console.warn(`Login attempt with incorrect password for user: ${username}`);
      return res.status(401).send('Invalid credentials.');
    }
    
    // Set session
    req.session.user = {
      username: user.username,
      role: user.role
    };
    
    console.log(`User logged in: ${username}`);
    res.status(200).send('Login successful.');
  } catch (err) {
    console.error('Error during user login:', err);
    res.status(500).send('Error logging in.');
  }
});

// User Logout
router.post('/logout', (req, res) => {
  if (req.session.user) {
    const username = req.session.user.username;
    req.session.destroy(err => {
      if (err) {
        console.error(`Error destroying session for user: ${username}`, err);
        return res.status(500).send('Error logging out.');
      }
      res.clearCookie('connect.sid');
      console.log(`User logged out: ${username}`);
      res.status(200).send('Logout successful.');
    });
  } else {
    res.status(400).send('No active session.');
  }
});

module.exports = router;
