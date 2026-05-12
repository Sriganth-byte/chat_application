import { useState, useEffect } from 'react'
import { Search as SearchIcon, User, MessageSquare, Hash, Loader2 } from 'lucide-react'
import api from '../api/axios'
import PostCard from '../components/PostCard'
import { formatDistanceToNow } from 'date-fns'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState('people')
  const [results, setResults] = useState({ users: [], messages: [], rooms: [] })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!query.trim()) { setResults({ users: [], messages: [], rooms: [] }); return }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const { data } = await api.get(`/chat/search/?q=${encodeURIComponent(query)}&type=all`)
        setResults(data)
      } catch {}
      setLoading(false)
    }, 400)
    return () => clearTimeout(timer)
  }, [query])

  const tabs = [
    { key: 'people', label: 'People', icon: User, count: results.users?.length || 0 },
    { key: 'groups', label: 'Groups', icon: MessageSquare, count: results.rooms?.length || 0 },
    { key: 'messages', label: 'Messages', icon: Hash, count: results.messages?.length || 0 },
  ]

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 16 }}>Search</h1>

      <div className="search-bar" style={{ marginBottom: 20 }}>
        <SearchIcon size={18} color="var(--text-muted)" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search people, groups, messages..."
          autoFocus
        />
        {loading && <Loader2 size={16} className="spin" color="var(--text-muted)" />}
      </div>

      {query.trim() && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {tabs.map(t => {
              const Icon = t.icon
              return (
                <button key={t.key} onClick={() => setTab(t.key)} className={`btn btn-sm ${tab === t.key ? 'btn-primary' : 'btn-secondary'}`}>
                  <Icon size={14} /> {t.label}
                  {t.count > 0 && <span style={{ marginLeft: 4, opacity: 0.7 }}>({t.count})</span>}
                </button>
              )
            })}
          </div>

          {tab === 'people' && (
            <div className="card">
              {(results.users || []).length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}><p>No users found</p></div>
              ) : (results.users || []).map(u => (
                <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                  <a href={`/profile/${u.username}`}>
                    <div className="avatar avatar-md">
                      {u.avatar_url ? <img src={u.avatar_url} alt="" /> : <span>{u.username?.[0]?.toUpperCase()}</span>}
                    </div>
                  </a>
                  <div style={{ flex: 1 }}>
                    <a href={`/profile/${u.username}`} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.username}</a>
                    {u.bio && <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{u.bio}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'groups' && (
            <div className="card">
              {(results.rooms || []).length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}><p>No groups found</p></div>
              ) : (results.rooms || []).map(r => (
                <div key={r.id} style={{ padding: '12px 0', borderBottom: '1px solid var(--border)', display: 'flex', gap: 12 }}>
                  <div className="avatar avatar-md">
                    <span>{r.name?.[0]?.toUpperCase() || '#'}</span>
                  </div>
                  <div>
                    <div style={{ fontWeight: 600 }}>{r.name}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.description || 'No description'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'messages' && (
            <div className="card">
              {(results.messages || []).length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}><p>No messages found</p></div>
              ) : (results.messages || []).map(m => (
                <div key={m.id} style={{ padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{m.sender?.username}</span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {formatDistanceToNow(new Date(m.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{m.content}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!query.trim() && (
        <div className="empty-state" style={{ padding: 60 }}>
          <SearchIcon size={48} />
          <h3>Search MindConnect</h3>
          <p>Find people, groups, and conversations</p>
        </div>
      )}
    </div>
  )
}
