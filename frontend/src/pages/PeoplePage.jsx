import { useState, useEffect, useCallback } from 'react'
import { Users, UserPlus, UserMinus, Check, X, Search, UserCheck, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import toast from 'react-hot-toast'

// ─── Avatar ───────────────────────────────────────────────────────────────────
function Avatar({ user, size = 44 }) {
  const initials = (user?.username?.[0] || '?').toUpperCase()
  return (
    <div
      className="avatar"
      style={{ width: size, height: size, minWidth: size, borderRadius: '50%', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--primary)', color: '#fff', fontWeight: 700, fontSize: size * 0.38 }}
    >
      {user?.avatar_url
        ? <img src={user.avatar_url} alt={user.username} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        : <span>{initials}</span>
      }
    </div>
  )
}

// ─── Request Card ─────────────────────────────────────────────────────────────
function RequestCard({ request, onAccept, onReject }) {
  const [loading, setLoading] = useState(null)
  const sender = request.sender

  const handle = async (action) => {
    setLoading(action)
    try {
      await api.patch(`/social/friend-request/${request.id}/`, { action })
      if (action === 'accept') {
        toast.success(`You and ${sender?.username} are now friends! 🎉`)
        onAccept(request)
      } else {
        toast.success('Request declined')
        onReject(request)
      }
    } catch (e) {
      toast.error(e?.response?.data?.error || 'Failed')
    }
    setLoading(null)
  }

  if (!sender) return null

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 0', borderBottom: '1px solid var(--border)' }}>
      <Link to={`/profile/${sender.username}`}>
        <Avatar user={sender} />
      </Link>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Link to={`/profile/${sender.username}`} style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>
          {sender.username}
        </Link>
        {sender.bio && (
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {sender.bio}
          </p>
        )}
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3, marginTop: 4 }}>
          <Clock size={10} /> Pending friend request
        </span>
      </div>
      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
        <button
          className="btn btn-primary btn-sm"
          onClick={() => handle('accept')}
          disabled={loading !== null}
        >
          <Check size={13} /> {loading === 'accept' ? '…' : 'Accept'}
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => handle('reject')}
          disabled={loading !== null}
        >
          <X size={13} /> {loading === 'reject' ? '…' : 'Decline'}
        </button>
      </div>
    </div>
  )
}

// ─── User Row ─────────────────────────────────────────────────────────────────
function UserRow({ user, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
      <Link to={`/profile/${user.username}`}>
        <Avatar user={user} />
      </Link>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Link to={`/profile/${user.username}`} style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>
          {user.username}
          {user.is_verified && <span style={{ marginLeft: 5, color: '#3b82f6' }}>✓</span>}
        </Link>
        {user.bio && (
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user.bio}
          </p>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{action}</div>
    </div>
  )
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyState({ icon: Icon, message }) {
  return (
    <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
      <Icon size={36} style={{ opacity: 0.35, marginBottom: 10 }} />
      <p style={{ fontWeight: 500, fontSize: '0.95rem' }}>{message}</p>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function PeoplePage() {
  const [tab, setTab] = useState('suggestions')
  const [suggestions, setSuggestions] = useState([])
  const [friends, setFriends] = useState([])
  const [requests, setRequests] = useState([])
  const [sentIds, setSentIds] = useState(new Set())
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [reqLoading, setReqLoading] = useState(false)

  // Initial load: suggestions + friends + requests
  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get('/social/suggestions/').then(r => setSuggestions(r.data?.results || r.data || [])).catch(() => setSuggestions([])),
      api.get('/social/friends/').then(r => setFriends(r.data?.results || r.data || [])).catch(() => setFriends([])),
      api.get('/social/friend-requests/?direction=received').then(r => setRequests(r.data?.results || r.data || [])).catch(() => setRequests([])),
    ]).finally(() => setLoading(false))
  }, [])

  // Reload requests fresh every time Requests tab is opened
  const loadRequests = useCallback(async () => {
    setReqLoading(true)
    try {
      const { data } = await api.get('/social/friend-requests/?direction=received')
      setRequests(data?.results || data || [])
    } catch {
      setRequests([])
    }
    setReqLoading(false)
  }, [])

  useEffect(() => {
    if (tab === 'requests') loadRequests()
  }, [tab, loadRequests])

  // Search
  useEffect(() => {
    if (!search.trim()) { setSearchResults([]); return }
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get(`/auth/users/?q=${encodeURIComponent(search.trim())}`)
        setSearchResults(data || [])
      } catch { setSearchResults([]) }
    }, 350)
    return () => clearTimeout(t)
  }, [search])

  const sendRequest = async (user) => {
    try {
      await api.post('/social/friend-request/', { user_id: user.id })
      setSentIds(s => new Set([...s, user.id]))
      setSuggestions(s => s.filter(u => u.id !== user.id))
      toast.success(`Request sent to ${user.username}! 👋`)
    } catch (e) {
      const resp = e?.response?.data || {}
      const msg = resp.error || ''
      if (msg.includes('Already friends')) {
        setSuggestions(s => s.filter(u => u.id !== user.id))
        setFriends(f => f.find(u => u.id === user.id) ? f : [...f, user])
        toast.success(`Already friends with ${user.username}`)
      } else if (resp.direction === 'received') {
        setSuggestions(s => s.filter(u => u.id !== user.id))
        if (resp.request) setRequests(rs => rs.find(r => r.id === resp.request.id) ? rs : [resp.request, ...rs])
        setTab('requests')
        toast(`${user.username} already sent you a request!`, { icon: '👆', duration: 4000 })
      } else if (resp.direction === 'sent') {
        setSentIds(s => new Set([...s, user.id]))
        setSuggestions(s => s.filter(u => u.id !== user.id))
        toast('Request already sent', { icon: '⏳' })
      } else {
        toast.error(msg || 'Failed')
      }
    }
  }

  const unfriend = async (user) => {
    try {
      await api.delete(`/social/friends/${user.id}/`)
      setFriends(f => f.filter(u => u.id !== user.id))
      toast.success('Unfriended')
    } catch { toast.error('Failed') }
  }

  // ─── Derived lists ───────────────────────────────────────────────────────────
  const showSearch = search.trim().length > 0
  const listUsers = showSearch ? searchResults
    : tab === 'suggestions' ? suggestions
    : tab === 'friends' ? friends
    : []

  const tabs = [
    { key: 'suggestions', label: 'Discover',  Icon: UserPlus  },
    { key: 'requests',    label: 'Requests',  Icon: UserCheck, badge: requests.length },
    { key: 'friends',     label: 'Friends',   Icon: Users,     badge: friends.length  },
  ]

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 20 }}>People</h1>

      {/* Search bar */}
      <div className="search-bar" style={{ marginBottom: 16 }}>
        <Search size={16} color="var(--text-muted)" />
        <input
          placeholder="Search people…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && (
          <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0 4px' }}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Tab buttons — hidden while searching */}
      {!showSearch && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {tabs.map(({ key, label, Icon, badge }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`btn btn-sm ${tab === key ? 'btn-primary' : 'btn-secondary'}`}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Icon size={13} />
              {label}
              {badge > 0 && (
                <span style={{
                  background: key === 'requests' ? '#ef4444' : 'rgba(255,255,255,0.2)',
                  color: 'white', fontSize: '0.65rem', fontWeight: 700,
                  padding: '1px 6px', borderRadius: 999,
                }}>
                  {badge}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Content card */}
      <div className="card" style={{ padding: '0 16px' }}>
        {loading ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
        ) : (

          /* ── REQUESTS TAB ── */
          (!showSearch && tab === 'requests') ? (
            reqLoading ? (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>Loading requests…</div>
            ) : requests.length === 0 ? (
              <EmptyState icon={UserCheck} message="No pending friend requests" />
            ) : (
              requests.map(req => (
                <RequestCard
                  key={req.id}
                  request={req}
                  onAccept={r => {
                    setRequests(rs => rs.filter(x => x.id !== r.id))
                    if (r.sender) setFriends(f => [...f, r.sender])
                  }}
                  onReject={r => setRequests(rs => rs.filter(x => x.id !== r.id))}
                />
              ))
            )
          ) : (

          /* ── SUGGESTIONS / FRIENDS / SEARCH ── */
            listUsers.length === 0 ? (
              <EmptyState
                icon={Users}
                message={
                  showSearch ? 'No users found'
                  : tab === 'friends' ? 'No friends yet — send some requests!'
                  : 'No suggestions right now'
                }
              />
            ) : (
              listUsers.map(user => (
                <UserRow
                  key={user.id}
                  user={user}
                  action={
                    tab === 'friends' && !showSearch ? (
                      <button className="btn btn-secondary btn-sm" onClick={() => unfriend(user)}>
                        <UserMinus size={13} /> Unfriend
                      </button>
                    ) : sentIds.has(user.id) ? (
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Clock size={12} /> Sent
                      </span>
                    ) : (
                      <button className="btn btn-primary btn-sm" onClick={() => sendRequest(user)}>
                        <UserPlus size={13} /> Add
                      </button>
                    )
                  }
                />
              ))
            )
          )
        )}
      </div>
    </div>
  )
}
