# Base2 Backend API (Legacy / Deprecated)

This Node/Express backend is retained for historical reference. The active stack uses FastAPI (`api/`) + Django (`django/`) behind Traefik.

Node.js/Express authentication backend with PostgreSQL database, JWT tokens, and email verification.

---

## 🚀 Features

- **Dual Authentication**: Email/password + Google OAuth
- **Email Verification**: Mandatory email verification for new users
- **Password Reset**: Secure token-based password reset
- **JWT Tokens**: Stateless authentication
- **Security**: bcrypt hashing, rate limiting, helmet.js, CORS
- **PostgreSQL**: Robust database with proper indexing
- **Email Service**: Nodemailer with customizable templates
- **Docker Ready**: Fully containerized

---

## 📋 API Endpoints

### **Public Endpoints**

#### Register New User

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John Doe"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Registration successful! Please check your email to verify your account.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "emailVerified": false
  }
}
```

#### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response:**

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "emailVerified": true,
    "authProvider": "email"
  }
}
```

#### Verify Email

```http
GET /api/auth/verify-email/:token
```

#### Resend Verification Email

```http
POST /api/auth/resend-verification
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Request Password Reset

```http
POST /api/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Reset Password

```http
POST /api/auth/reset-password/:token
Content-Type: application/json

{
  "password": "NewSecurePass123"
}
```

#### Google OAuth Login/Signup

```http
POST /api/auth/google
Content-Type: application/json

{
  "googleId": "1234567890",
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://..."
}
```

### **Protected Endpoints**

#### Get Current User

```http
GET /api/auth/me
Authorization: Bearer <token>
```

**Response:**

```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "picture": null,
    "emailVerified": true,
    "authProvider": "email",
    "bio": null,
    "location": null,
    "website": null,
    "created_at": "2024-01-01T00:00:00.000Z"
  }
}
```

---

## 🔐 Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

---

## 🐳 Docker Setup (Recommended)

The backend is fully integrated with Docker Compose:

```bash
# Start all services (from project root)
./scripts/start.sh --build

# Backend runs on: http://localhost:5001
# Database automatically initialized on first run
```

**What happens automatically:**

1. PostgreSQL container starts with authentication schema
2. Backend connects to database
3. All services networked together
4. Health checks ensure everything is running

---

## 💻 Local Development (Without Docker)

### Prerequisites

- Node.js 18+
- PostgreSQL 16+
- npm or yarn

### 1. Install Dependencies

```bash
cd backend
npm install
```

### 2. Setup Database

```bash
# Create database
psql -U postgres
CREATE DATABASE mydatabase;
\q

# Run schema
psql -U myuser -d mydatabase -f database/schema.sql
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Start Server

```bash
# Development (with nodemon)
npm run dev

# Production
npm start
```

Server runs on: `http://localhost:5001`

---

## 📧 Email Configuration

### Gmail Setup (Development)

1. **Enable 2-Step Verification:**
   - Go to Google Account > Security
   - Turn on 2-Step Verification

2. **Generate App Password:**
   - Go to Security > App passwords
   - Select app: Mail
   - Select device: Other
   - Copy the 16-character password

3. **Update .env:**

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
EMAIL_FROM=noreply@base2.com
```

### Other Email Services

**SendGrid:**

```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USER=apikey
EMAIL_PASSWORD=your_sendgrid_api_key
```

**Mailgun:**

```env
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USER=your_mailgun_username
EMAIL_PASSWORD=your_mailgun_password
```

---

## 🔑 JWT Configuration

Generate a secure JWT secret:

```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

Add to `.env`:

```env
JWT_SECRET=your_generated_secret_here
JWT_EXPIRE=7d
```

---

## 🛡️ Security Features

### Implemented:

- ✅ **Password Hashing** - bcrypt with salt rounds
- ✅ **JWT Tokens** - Stateless authentication
- ✅ **Rate Limiting** - 100 requests per 15 minutes
- ✅ **Helmet.js** - Security headers
- ✅ **CORS** - Configured for frontend origin
- ✅ **Input Validation** - express-validator
- ✅ **SQL Injection Protection** - Parameterized queries
- ✅ **Email Verification** - Required for new accounts

### Production Checklist:

- [ ] Change JWT_SECRET to strong random value
- [ ] Set NODE_ENV=production
- [ ] Use HTTPS only
- [ ] Configure proper CORS origins
- [ ] Set up proper email service (not Gmail)
- [ ] Enable database backups
- [ ] Set up error monitoring (Sentry, etc.)
- [ ] Configure logging service
- [ ] Set up SSL certificates

---

## 📊 Database Schema

Tables automatically created on first run:

### **users**

- Authentication and profile data
- Support for both email and OAuth
- Email verification tracking
- Password reset tokens

### **sessions** (optional)

- Track active user sessions
- IP address and user agent logging

See `database/schema.sql` for complete schema.

---

## 🧪 Testing Endpoints

### Health Check

```bash
curl http://localhost:5001/api/health
```

### Register User

```bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234",
    "name": "Test User"
  }'
```

### Login

```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234"
  }'
```

### Get Current User

```bash
curl http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📝 Environment Variables

| Variable                | Description        | Default               |
| ----------------------- | ------------------ | --------------------- |
| PORT                    | Server port        | 5000                  |
| NODE_ENV                | Environment        | development           |
| DB_HOST                 | PostgreSQL host    | localhost             |
| DB_PORT                 | PostgreSQL port    | 5432                  |
| DB_NAME                 | Database name      | mydatabase            |
| DB_USER                 | Database user      | myuser                |
| DB_PASSWORD             | Database password  | mypassword            |
| JWT_SECRET              | JWT signing key    | (required)            |
| JWT_EXPIRE              | Token expiration   | 7d                    |
| EMAIL_HOST              | SMTP host          | smtp.gmail.com        |
| EMAIL_PORT              | SMTP port          | 587                   |
| EMAIL_USER              | SMTP username      | (required)            |
| EMAIL_PASSWORD          | SMTP password      | (required)            |
| EMAIL_FROM              | From email address | noreply@base2.com     |
| FRONTEND_URL            | Frontend URL       | http://localhost:3000 |
| RATE_LIMIT_WINDOW_MS    | Rate limit window  | 900000                |
| RATE_LIMIT_MAX_REQUESTS | Max requests       | 100                   |

---

## 🐛 Troubleshooting

### Database Connection Failed

```
❌ Unexpected database error
```

**Solution:** Check PostgreSQL is running and credentials in `.env` are correct

### Email Not Sending

```
❌ Error sending verification email
```

**Solution:**

- Check Gmail app password is correct
- Verify 2FA is enabled
- Check EMAIL_USER and EMAIL_PASSWORD in `.env`

### JWT Token Invalid

```
401 Unauthorized - Invalid token
```

**Solution:**

- Check token is being sent in Authorization header
- Verify JWT_SECRET matches between requests
- Token may be expired (check JWT_EXPIRE)

### Port Already in Use

```
EADDRINUSE: address already in use :::5000
```

**Solution:**

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

---

## 📚 Tech Stack

- **Runtime:** Node.js 18
- **Framework:** Express 4
- **Database:** PostgreSQL 16
- **Authentication:** JWT + bcrypt
- **Email:** Nodemailer
- **Validation:** express-validator
- **Security:** Helmet, CORS, rate-limit
- **Database Client:** pg (node-postgres)

---

## 🤝 Integration with React App

The React app should:

1. Store JWT token in localStorage
2. Include token in Authorization header: `Bearer <token>`
3. Handle token expiration and refresh
4. Redirect to login on 401 responses

Example:

```javascript
// API call with auth
const response = await fetch('http://localhost:5001/api/auth/me', {
  headers: {
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  },
});
```

---

## 📖 Further Documentation

- [Google OAuth Setup](../react-app/OAUTH_SETUP.md)
- [PostgreSQL Schema](./database/schema.sql)
- [Environment Variables](../.env.example)

---

## 🎉 Ready to Use!

Your authentication backend is production-ready with:

- ✅ Dual authentication (Email + OAuth)
- ✅ Email verification system
- ✅ Password reset flow
- ✅ Secure password hashing
- ✅ JWT token authentication
- ✅ Rate limiting
- ✅ Docker integration
- ✅ Comprehensive API

Start the server and begin building! 🚀
