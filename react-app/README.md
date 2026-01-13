# Base2 React App with Google OAuth

A modern React application featuring Google OAuth authentication, protected routes, and a complete user management system.

---

## ✨ Features

### 🔐 Authentication

- **Google OAuth Integration** - Secure login with Google accounts
- **Session Management** - Persistent user sessions with localStorage
- **Protected Routes** - Route guards for authenticated-only pages
- **Auto-redirect** - Seamless navigation based on auth status

### 📄 Pages

- **Home** - Public landing page with Google login
- **Dashboard** - Protected page with statistics and quick actions
- **User Settings** - Profile management and account settings

### 🎨 UI/UX

- **Modern Design** - Clean, professional interface
- **Responsive Layout** - Works on all devices
- **Smooth Animations** - Polished user experience
- **Custom Styling** - Gradient backgrounds and hover effects

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Set Up Google OAuth

Follow the detailed guide: [OAUTH_SETUP.md](./OAUTH_SETUP.md)

Quick summary:

1. Create a Google Cloud project
2. Enable Google+ API
3. Configure OAuth consent screen
4. Create OAuth 2.0 credentials
5. Copy your Client ID

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Google Client ID:

```env
REACT_APP_GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
```

### 4. Start Development Server

```bash
npm start
```

The app will open at `http://localhost:3000`

---

## 🧊 Glass Portfolio Quickstart

### Prereqs

- Tailwind and PostCSS are preconfigured
- Glass tokens live in `src/styles/tokens.css`
- Base glass styles in `src/styles/glass.css` (imported via `App.css`)

### Run & Test

```bash
npm run build
npm run test:ci
```

### Key Files

- `src/components/glass/ThemeToggle.tsx` – theme switch (dark/light)
- `src/contexts/ThemeContext.js` – theme provider with cookie persistence
- `src/components/home/HomeHero.jsx` – hero section
- `src/components/portfolio/*` – About, Projects, Contact
- `src/components/SectionContainer.jsx` – spacing/container helper

### Accessibility

- Focus-visible rings: `.focus-ring` and `.glass-focus` classes
- Contrast and keyboard navigation validated in components

---

## 📁 Project Structure

```
react-app/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Navigation.js      # Navigation bar component
│   │   └── ProtectedRoute.js  # Route protection wrapper
│   ├── contexts/
│   │   └── AuthContext.js     # Authentication state management
│   ├── pages/
│   │   ├── Home.js            # Landing page with OAuth login
│   │   ├── Dashboard.js       # Main dashboard (protected)
│   │   └── UserSettings.js    # User settings page (protected)
│   ├── App.js                 # Main app component with routing
│   ├── App.css                # App-specific styles
│   ├── index.js               # React entry point
│   └── index.css              # Global styles
├── .env.example               # Environment variables template
├── package.json               # Dependencies and scripts
├── OAUTH_SETUP.md            # Detailed OAuth setup guide
└── README.md                 # This file
```

---

## 🛠️ Tech Stack

### Core

- **React 18** - UI library
- **React Router v6** - Client-side routing
- **React Context API** - State management

### Authentication

- **@react-oauth/google** - Google OAuth integration
- **jwt-decode** - JWT token decoding

### HTTP Client

- **Axios** - HTTP requests

### Styling

- **CSS-in-JS** - Inline styles with JavaScript objects
- **Custom CSS** - Global styles and animations

---

## 📖 Usage Guide

### Authentication Flow

1. **Login:**
   - Visit home page
   - Click "Sign in with Google"
   - Select Google account
   - Grant permissions
   - Redirected to Dashboard

2. **Protected Routes:**
   - Dashboard and Settings require authentication
   - Unauthenticated users redirect to Home
   - Session persists across page reloads

3. **Logout:**
   - Click "Logout" button in navigation
   - Clears user session
   - Redirects to Home page

### Accessing Pages

- **Home:** `http://localhost:3000/`
- **Dashboard:** `http://localhost:3000/dashboard` (requires login)
- **Settings:** `http://localhost:3000/settings` (requires login)

---

## 🔧 Available Scripts

### `npm start`

Runs the app in development mode at `http://localhost:3000`

### `npm test`

Launches the test runner in interactive watch mode

### `npm run build`

Builds the app for production to the `build` folder

### `npm run eject`

**Warning:** This is a one-way operation!

---

## 🎨 Customization

### Changing Colors

Edit the gradient colors in component styles:

```javascript
background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
```

### Modifying Layout

All pages use inline styles that can be easily customized in their respective files.

### Adding New Routes

1. Create new page component in `src/pages/`
2. Add route in `src/App.js`:

```javascript
<Route
  path="/new-page"
  element={
    <ProtectedRoute>
      <NewPage />
    </ProtectedRoute>
  }
/>
```

3. Add navigation link in `src/components/Navigation.js`

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** OAuth errors  
**Solution:** See [OAUTH_SETUP.md](./OAUTH_SETUP.md) troubleshooting section

**Issue:** Environment variables not loading  
**Solution:** Restart dev server after changing `.env`

**Issue:** Dependencies not found  
**Solution:** Run `npm install`

**Issue:** Port already in use  
**Solution:** Kill process on port 3000 or use different port

---

## 🔒 Security Considerations

### Development

- ✅ `.env` file is gitignored
- ✅ Using localhost for testing
- ✅ Test users only in OAuth consent screen

### Production

- ⚠️ Update OAuth origins to production domain
- ⚠️ Use HTTPS only
- ⚠️ Implement proper error handling
- ⚠️ Add rate limiting for API calls
- ⚠️ Validate and sanitize all user inputs
- ⚠️ Use environment variables on hosting platform

---

## 📦 Dependencies

```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.20.0",
  "@react-oauth/google": "^0.12.1",
  "axios": "^1.6.0",
  "react-scripts": "^5.0.1"
}
```

---

## 🚢 Deployment

### Build for Production

```bash
npm run build
```

### Deploy to Hosting Platform

1. **Vercel / Netlify:**
   - Connect your repository
   - Set environment variable: `REACT_APP_GOOGLE_CLIENT_ID`
   - Deploy

2. **Update OAuth Settings:**
   - Add production domain to Authorized JavaScript origins
   - Add production domain to Authorized redirect URIs

3. **Move to Production:**
   - Update OAuth consent screen from "Testing" to "Production"
   - Add privacy policy and terms of service URLs

---

## 📚 Learn More

- [React Documentation](https://react.dev/)
- [React Router Documentation](https://reactrouter.com/)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Create React App Documentation](https://create-react-app.dev/)

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📝 License

This project is part of the Base2 Docker Environment.

---

## 🎉 You're Ready!

Your React app with Google OAuth is now set up and ready to use. Happy coding! 🚀
