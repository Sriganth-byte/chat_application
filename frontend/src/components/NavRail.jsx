import { NavLink, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import {
  Home, MessageSquare, Users, Bookmark, Search,
  Settings, LogOut, Compass, Shield
} from 'lucide-react'

export default function NavRail() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const initials = user?.username?.[0]?.toUpperCase() || '?'

  const navItems = [
    { to: '/',            icon: Home,          label: 'Feed' },
    { to: '/explore',     icon: Compass,       label: 'Explore' },
    { to: '/chat',        icon: MessageSquare, label: 'Messages' },
    { to: '/people',      icon: Users,         label: 'Friends' },
    { to: '/saved',       icon: Bookmark,      label: 'Saved' },
    { to: '/search',      icon: Search,        label: 'Search' },
    ...(user?.is_staff || user?.is_superuser ? [{ to: '/admin', icon: Shield, label: 'Admin' }] : []),
  ]

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <nav className="nav-rail">
      {/* Logo */}
      <div className="nav-logo" title="MindConnect">M</div>

      {/* Navigation Links */}
      <div className="nav-items">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title={label}
          >
            <Icon size={22} strokeWidth={1.8} />
          </NavLink>
        ))}
      </div>

      {/* Bottom section */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, paddingBottom: 8 }}>
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Settings">
          <Settings size={22} strokeWidth={1.8} />
        </NavLink>

        <button className="nav-item" title="Logout" onClick={handleLogout}
          style={{ width: 48, height: 48 }}>
          <LogOut size={20} strokeWidth={1.8} />
        </button>

        <NavLink to={`/profile/${user?.username}`} className="nav-user" title={user?.username}>
          {user?.avatar ? (
            <img src={user.avatar_url || user.avatar} alt="avatar" />
          ) : (
            <div className="nav-user-placeholder">{initials}</div>
          )}
        </NavLink>
      </div>
    </nav>
  )
}
