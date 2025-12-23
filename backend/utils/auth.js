const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

// Hash password
const hashPassword = async (password) => {
  const salt = await bcrypt.genSalt(10);
  return await bcrypt.hash(password, salt);
};

// Compare password
const comparePassword = async (password, hashedPassword) => {
  return await bcrypt.compare(password, hashedPassword);
};

// Generate JWT token
// Accepts either a numeric userId or an object payload.
// Includes both `id` (legacy) and `userId` (explicit) for compatibility.
const generateToken = (payload) => {
  const userId = typeof payload === 'object' && payload !== null ? payload.userId : payload;
  const email = typeof payload === 'object' && payload !== null ? payload.email : undefined;

  return jwt.sign(
    { id: userId, userId, email },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRE || '7d' }
  );
};

// Verify JWT token
// Throws on invalid/expired tokens.
const verifyToken = (token) => jwt.verify(token, process.env.JWT_SECRET);

// Generate random token for email verification
const generateVerificationToken = () => {
  return crypto.randomBytes(32).toString('hex');
};

// Generate token expiry time (24 hours from now)
const generateTokenExpiry = (hours = 24) => {
  return new Date(Date.now() + hours * 60 * 60 * 1000);
};

module.exports = {
  hashPassword,
  comparePassword,
  generateToken,
  verifyToken,
  generateVerificationToken,
  generateTokenExpiry,
};
