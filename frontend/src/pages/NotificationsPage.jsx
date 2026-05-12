import { useState, useEffect } from 'react'
import { Bell, Check, CheckCheck, User, Heart, MessageCircle, UserPlus } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import api from '../api/axios'
import useNotificationStore from '../store/notificationStore'

const NOTIFICATION_ICONS = {
  message:       { icon: MessageCircle, color: 'var(--primary)' },
  mention:       { icon: MessageCircle, color: 'var(--secondary)' },
  group_invite:  { icon: User, color: 'var(--info)' },
  friend_request:{ icon: UserPlus, color: 'var(--success)' },
  friend_accepted:{icon: UserPlus, color: 'var(--success)' },
  new_follower:  { icon: User, color: 'var(--secondary)' },
  post_like:     { icon: Heart, color: 'var(--danger)' },
  post_comment:  { icon: MessageCircle, color: 'var(--primary)' },
  system:        { icon: Bell, color: 'var(--warning)' },
}

function NotifIcon({ type }) {
  const config = NOTIFICATION_ICONS[type] || NOTIFICATION_ICONS.system
  const Icon = config.icon
  return (
    <div style={{
      width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
      background: `${config.color}20`,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <Icon size={18} color={config.color} strokeWidth={2} />
    </div>
  )
}

export default function NotificationsPage() {
  const { notifications, loading, fetchNotifications, markRead, markAllRead } = useNotificationStore()

  useEffect(() => { fetchNotifications() }, [fetchNotifications])

  const unread = notifications.filter(n => !n.is_read).length

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Notifications</h1>
          {unread > 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{unread} unread</p>
          )}
        </div>
        {unread > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={markAllRead}>
            <CheckCheck size={16} /> Mark all read
          </button>
        )}
      </div>

      {/* Notifications List */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <div className="spin" style={{ width: 32, height: 32, border: '3px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%' }} />
        </div>
      ) : notifications.length === 0 ? (
        <div className="empty-state">
          <Bell size={48} />
          <h3>All caught up!</h3>
          <p>No notifications yet. Start connecting with people!</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {notifications.map((notif, i) => (
            <div key={notif.id}>
              <div
                className={`notification-item ${!notif.is_read ? 'unread' : ''}`}
                onClick={() => !notif.is_read && markRead(notif.id)}
              >
                <NotifIcon type={notif.type} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginBottom: 2, lineHeight: 1.4 }}>
                    {notif.message}
                  </p>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })}
                  </span>
                </div>
                {!notif.is_read && (
                  <button
                    onClick={e => { e.stopPropagation(); markRead(notif.id) }}
                    className="btn btn-ghost btn-icon"
                    title="Mark as read"
                  >
                    <Check size={16} />
                  </button>
                )}
              </div>
              {i < notifications.length - 1 && <div className="divider" style={{ margin: 0 }} />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
