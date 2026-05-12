import { useState, useEffect } from 'react'
import { UserPlus, Users } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'

export default function SuggestionsPanel() {
  const [suggestions, setSuggestions] = useState([])

  useEffect(() => {
    api.get('/social/suggestions/').then(r => setSuggestions(r.data.slice(0, 5))).catch(() => {})
  }, [])

  const sendRequest = async (user) => {
    try {
      await api.post('/social/friend-request/', { user_id: user.id })
      setSuggestions(s => s.filter(u => u.id !== user.id))
      toast.success(`Request sent to ${user.username}`)
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed')
    }
  }

  if (suggestions.length === 0) return null

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Users size={18} color="var(--primary)" />
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          People You May Know
        </h3>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {suggestions.map(u => {
          const initials = u.username?.[0]?.toUpperCase() || '?'
          return (
            <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <a href={`/profile/${u.username}`}>
                <div className="avatar avatar-sm">
                  {u.avatar_url ? <img src={u.avatar_url} alt="" /> : <span>{initials}</span>}
                </div>
              </a>
              <a href={`/profile/${u.username}`} style={{ flex: 1, fontWeight: 500, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                {u.username}
              </a>
              <button className="btn btn-secondary btn-sm" style={{ padding: '4px 10px' }} onClick={() => sendRequest(u)}>
                <UserPlus size={13} />
              </button>
            </div>
          )
        })}
        <a href="/people" style={{ fontSize: '0.8rem', color: 'var(--primary)', marginTop: 4, display: 'block', textAlign: 'center' }}>
          See all suggestions →
        </a>
      </div>
    </div>
  )
}
