// src/server.js

require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const { Pool } = require('pg');
const http = require('http');
const { Server } = require('socket.io');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const winston = require('winston');

// Initialize Express app
const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Configure Winston logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    // Add file transports or external logging services if needed
  ],
});

// Middleware for logging requests
app.use((req, res, next) => {
  logger.info(`Incoming request: ${req.method} ${req.url}`);
  next();
});

// Use morgan for HTTP request logging
app.use(morgan('combined'));

// Parse incoming JSON and URL-encoded data
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from the 'public' directory
app.use(express.static(path.join(__dirname, '../public')));

// Rate Limiting Middleware
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again after 15 minutes.',
});
app.use(limiter);

// Session Configuration
app.use(session({
  secret: process.env.SESSION_SECRET, // Must be set in environment variables
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production', // Ensures cookies are sent over HTTPS
    httpOnly: true, // Prevents client-side JavaScript from accessing the cookie
    sameSite: 'lax', // Helps protect against CSRF
    maxAge: 1000 * 60 * 60 * 24, // 1 day
  }
}));

// Initialize PostgreSQL pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false, // Required for Fly.io
  },
});

// Test database connection
pool.connect((err, client, release) => {
  if (err) {
    logger.error('Error acquiring client', err.stack);
    process.exit(1); // Exit if database connection fails
  }
  logger.info('Connected to PostgreSQL database.');
  release();
});

// Authentication Middleware to protect routes
function isAuthenticated(req, res, next) {
  if (req.session && req.session.user) {
    return next();
  } else {
    return res.status(401).send('Unauthorized');
  }
}

// Import and use authentication routes
const authRoutes = require('./routes/authRoutes');
app.use('/auth', authRoutes);

// Home Route
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public', 'index.html'));
});

// Driver Dashboard Route
app.get('/driver.html', isAuthenticated, (req, res) => {
  if (req.session.user.role !== 'driver') {
    return res.status(403).send('Access denied.');
  }
  res.sendFile(path.join(__dirname, '../public', 'driver.html'));
});

// Cashier Dashboard Route
app.get('/cashier.html', isAuthenticated, (req, res) => {
  if (req.session.user.role !== 'cashier') {
    return res.status(403).send('Access denied.');
  }
  res.sendFile(path.join(__dirname, '../public', 'cashier.html'));
});

// User Info Endpoint
app.get('/user', isAuthenticated, (req, res) => {
  res.json({
    username: req.session.user.username,
    role: req.session.user.role
  });
});

// Socket.io for Real-Time Communication
let socketToDriver = {};

io.on('connection', (socket) => {
  logger.info(`A user connected: ${socket.id}`);

  // Handle driver registration
  socket.on('registerDriver', (username) => {
    socketToDriver[socket.id] = username;
    logger.info(`Driver registered: ${username}`);
  });

  // Listen for driver location updates
  socket.on('driverLocation', async (data) => {
    const { username, latitude, longitude } = data;
    if (!username) {
      logger.error('Username is required for driverLocation event.');
      return;
    }

    try {
      const upsertQuery = `
        INSERT INTO drivers (username, latitude, longitude, timestamp)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (username)
        DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude, timestamp = EXCLUDED.timestamp
      `;
      await pool.query(upsertQuery, [username, latitude, longitude]);

      // Broadcast updated drivers to all cashiers
      const driversResult = await pool.query('SELECT username, latitude, longitude, timestamp FROM drivers');
      io.emit('updateDrivers', driversResult.rows);
      logger.info(`Updated location for driver: ${username}`);
    } catch (err) {
      logger.error('Error updating driver location:', err);
    }
  });

  // Handle disconnection
  socket.on('disconnect', async () => {
    logger.info(`User disconnected: ${socket.id}`);
    const username = socketToDriver[socket.id];
    if (username) {
      try {
        await pool.query('DELETE FROM drivers WHERE username = $1', [username]);
        io.emit('updateDrivers', []); // Optionally, update all cashiers about driver disconnection
        logger.info(`Driver removed: ${username}`);
      } catch (err) {
        logger.error('Error removing driver:', err);
      }
      delete socketToDriver[socket.id];
    }
  });
});

// Graceful Shutdown
function gracefulShutdown() {
  logger.info('\nShutting down gracefully...');
  server.close(() => {
    logger.info('HTTP server closed.');
    pool.end(() => {
      logger.info('Database pool closed.');
      process.exit(0);
    });
  });

  setTimeout(() => {
    logger.error('Forcing shutdown...');
    process.exit(1);
  }, 10000);
}

process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);

// Global Error Handler (Place after all routes)
app.use((err, req, res, next) => {
  logger.error('Global Error Handler:', err.stack);
  res.status(500).send('Something went wrong!');
});

// Start the Server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  logger.info(`Server is running on port ${PORT}`);
});
