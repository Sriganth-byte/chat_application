import { Home, Compass, MessageSquare, Users } from 'lucide-react'
import { NavLink } from 'react-router-dom'

export default function MobileBottomNav() {
  const items = [
    { to: '/',        icon: Home,          label: 'Home',     end: true },
    { to: '/explore', icon: Compass,       label: 'Explore' },
    { to: '/chat',    icon: MessageSquare, label: 'Messages' },
    { to: '/people',  icon: Users,         label: 'Friends' },
  ]

  return (
    <nav className="mobile-bottom-nav">
      <div className="mobile-bottom-nav__inner">
        {items.map(({ to, icon: Icon, label, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => `mobile-bottom-nav__item ${isActive ? 'active' : ''}`}>
            <div className="mobile-bottom-nav__icon">
              <Icon size={22} strokeWidth={1.8} />
            </div>
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
