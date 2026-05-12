import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import useAuthStore from './store/authStore'
import useNotificationStore from './store/notificationStore'

// Auth pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

// App pages
import FeedPage from './pages/FeedPage'
import ChatPage from './pages/ChatPage'
import ProfilePage from './pages/ProfilePage'
import NotificationsPage from './pages/NotificationsPage'
import PeoplePage from './pages/PeoplePage'
import SearchPage from './pages/SearchPage'
import SavedPage from './pages/SavedPage'
import SettingsPage from './pages/SettingsPage'
import ExplorePage from './pages/ExplorePage'
import HashtagPage from './pages/HashtagPage'
import AnalyticsDashboard from './pages/AnalyticsDashboard'
import AdminManagement from './pages/AdminManagement'

// Layout
import NavRail from './components/NavRail'
import MobileBottomNav from './components/MobileBottomNav'
import GlobalCallManager from './components/GlobalCallManager'
import useThemeStore from './store/themeStore'

function Guard({ children }) {
  const { user } = useAuthStore()
  return user ? children : <Navigate to="/login" replace />
}

function AdminGuard({ children }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  return user.is_staff || user.is_superuser ? children : <Navigate to="/" replace />
}

function AppShell({ children }) {
  const location = useLocation()
  const isChat = location.pathname.startsWith('/chat')
  return (
    <div className="app-shell">
      <NavRail />
      <div className={isChat ? 'main-content' : 'main-content page-scroll'}>
        {children}
      </div>
      <MobileBottomNav />
    </div>
  )
}

function AppInitializer() {
  const { user } = useAuthStore()
  const { fetchNotifications } = useNotificationStore()
  const { initTheme } = useThemeStore()

  useEffect(() => {
    initTheme()
    if (user) {
      fetchNotifications()
      // Poll notifications every 60s
      const interval = setInterval(fetchNotifications, 60000)
      return () => clearInterval(interval)
    }
  }, [user, fetchNotifications, initTheme])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInitializer />
      <GlobalCallManager />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font)',
            fontSize: '0.88rem',
          },
          success: { iconTheme: { primary: '#10b981', secondary: 'white' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: 'white' } },
        }}
      />
      <Routes>
        {/* Public routes */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected app routes */}
        <Route path="/" element={<Guard><AppShell><FeedPage /></AppShell></Guard>} />
        <Route path="/chat" element={<Guard><AppShell><ChatPage /></AppShell></Guard>} />
        <Route path="/profile/:username" element={<Guard><AppShell><ProfilePage /></AppShell></Guard>} />
        <Route path="/notifications" element={<Guard><AppShell><NotificationsPage /></AppShell></Guard>} />
        <Route path="/people" element={<Guard><AppShell><PeoplePage /></AppShell></Guard>} />
        <Route path="/search" element={<Guard><AppShell><SearchPage /></AppShell></Guard>} />
        <Route path="/saved" element={<Guard><AppShell><SavedPage /></AppShell></Guard>} />
        <Route path="/settings" element={<Guard><AppShell><SettingsPage /></AppShell></Guard>} />
        <Route path="/explore" element={<Guard><AppShell><ExplorePage /></AppShell></Guard>} />

        <Route path="/hashtag/:tag" element={<Guard><AppShell><HashtagPage /></AppShell></Guard>} />
        <Route path="/analytics" element={<Guard><AppShell><AnalyticsDashboard /></AppShell></Guard>} />
        <Route path="/admin" element={<AdminGuard><AppShell><AdminManagement /></AppShell></AdminGuard>} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
