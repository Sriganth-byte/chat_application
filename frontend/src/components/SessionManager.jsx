import { useState, useEffect } from 'react'
import { Smartphone, Monitor, Tablet, MapPin, AlertTriangle, LogOut, Shield, Clock } from 'lucide-react'
import api from '../api/axios'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

const DEVICE_ICONS = { mobile: Smartphone, tablet: Tablet, desktop: Monitor, unknown: Monitor }

export default function SessionManager() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [revoking, setRevoking] = useState(null)

  useEffect(() => { fetchSessions() }, [])

  const fetchSessions = async () => {
    try {
      const { data } = await api.get('/auth/sessions/')
      setSessions(data)
    } catch { toast.error('Could not load sessions') }
    setLoading(false)
  }

  const revoke = async (id) => {
    setRevoking(id)
    try {
      await api.delete(`/auth/sessions/${id}/`)
      setSessions(prev => prev.filter(s => s.id !== id))
      toast.success('Session revoked')
    } catch { toast.error('Failed to revoke') }
    setRevoking(null)
  }

  const revokeAll = async () => {
    if (!window.confirm('Sign out all other sessions?')) return
    try {
      await api.delete('/auth/sessions/all/')
      fetchSessions()
      toast.success('All sessions revoked')
    } catch { toast.error('Failed') }
  }

  if (loading) return <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Loading sessions…</p>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>Active Sessions</h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '4px 0 0' }}>
            {sessions.length} active session{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
        {sessions.length > 1 && (
          <button className="btn btn-danger btn-sm" onClick={revokeAll}>
            <LogOut size={13} /> Sign out all
          </button>
        )}
      </div>

      {sessions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)' }}>
          <Shield size={36} style={{ marginBottom: 12 }} />
          <p>No active sessions found</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sessions.map(s => {
            const DevIcon = DEVICE_ICONS[s.device_type] || Monitor
            return (
              <div key={s.id} style={{
                display: 'flex', gap: 14, alignItems: 'center', padding: '14px 16px',
                background: s.is_current ? 'rgba(108,99,255,0.07)' : 'var(--bg-hover)',
                border: `1px solid ${s.is_suspicious ? 'var(--danger)' : s.is_current ? 'var(--primary)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-md)',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: s.is_suspicious ? 'rgba(239,68,68,0.12)' : 'var(--bg-card)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                }}>
                  {s.is_suspicious
                    ? <AlertTriangle size={18} color="var(--danger)" />
                    : <DevIcon size={18} color="var(--primary)" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>
                      {s.browser} on {s.os} · {s.device_type}
                    </span>
                    {s.is_current && (
                      <span style={{ fontSize: '0.68rem', background: 'var(--primary)', color: 'white', padding: '1px 7px', borderRadius: 999, fontWeight: 600 }}>
                        Current
                      </span>
                    )}
                    {s.is_suspicious && (
                      <span style={{ fontSize: '0.68rem', background: 'var(--danger)', color: 'white', padding: '1px 7px', borderRadius: 999, fontWeight: 600 }}>
                        ⚠ Suspicious
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                      <MapPin size={10} /> {s.city || 'Unknown'}, {s.country || 'Unknown'} · {s.ip_address}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                      <Clock size={10} /> {formatDistanceToNow(new Date(s.logged_in_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
                {!s.is_current && (
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => revoke(s.id)}
                    disabled={revoking === s.id}
                    style={{ color: 'var(--danger)', flexShrink: 0 }}
                  >
                    <LogOut size={13} /> {revoking === s.id ? '…' : 'Revoke'}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
