import { useState, useEffect } from 'react'
import { TrendingUp, Hash, Users, Loader2, Search } from 'lucide-react'
import api from '../api/axios'
import PostCard from '../components/PostCard'
import { Link } from 'react-router-dom'

export default function ExplorePage() {
  const [tab, setTab] = useState('trending')
  const [posts, setPosts] = useState([])
  const [tags, setTags] = useState([])
  const [people, setPeople] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get('/posts/feed/').catch(() => ({ data: { results: [] } })),
      api.get('/posts/trending/').catch(() => ({ data: [] })),
      api.get('/auth/users/').catch(() => ({ data: [] })),
    ]).then(([postsRes, tagsRes, peopleRes]) => {
      setPosts(postsRes.data.results || postsRes.data || [])
      setTags(tagsRes.data || [])
      setPeople(peopleRes.data || [])
      setLoading(false)
    })
  }, [])

  const tabs = [
    { key: 'trending', label: 'Trending', icon: TrendingUp },
    { key: 'people', label: 'People', icon: Users },
    { key: 'tags', label: 'Hashtags', icon: Hash },
  ]

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '20px 16px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 4 }}>Explore</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>Discover people, posts, and trends</p>
      </div>

      {/* Search */}
      <div className="search-bar" style={{ marginBottom: 20 }}>
        <Search size={18} color="var(--text-muted)" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search people, hashtags, posts..."
        />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {tabs.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)}
            className={`btn btn-sm ${tab === key ? 'btn-primary' : 'btn-secondary'}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="spin" color="var(--primary)" />
        </div>
      ) : (
        <>
          {tab === 'trending' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {posts.length === 0 ? (
                <div className="empty-state">
                  <TrendingUp size={48} />
                  <h3>No trending posts yet</h3>
                  <p>Be the first to post something!</p>
                </div>
              ) : posts.map(p => <PostCard key={p.id} post={p} />)}
            </div>
          )}

          {tab === 'people' && (
            <div className="card">
              {people.length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}>
                  <Users size={40} />
                  <h3>No users found</h3>
                </div>
              ) : people.map(u => (
                <div key={u.id} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 0', borderBottom: '1px solid var(--border)'
                }}>
                  <Link to={`/profile/${u.username}`}>
                    <div className="avatar avatar-md">
                      {u.avatar_url ? <img src={u.avatar_url} alt="" /> : <span>{u.username?.[0]?.toUpperCase()}</span>}
                    </div>
                  </Link>
                  <div style={{ flex: 1 }}>
                    <Link to={`/profile/${u.username}`} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {u.username}
                    </Link>
                    {u.bio && <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{u.bio}</p>}
                  </div>
                  <Link to={`/profile/${u.username}`} className="btn btn-secondary btn-sm">View</Link>
                </div>
              ))}
            </div>
          )}

          {tab === 'tags' && (
            <div className="card">
              {tags.length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}>
                  <Hash size={40} />
                  <h3>No trending hashtags yet</h3>
                </div>
              ) : tags.map((t, i) => (
                <div key={t.tag} style={{
                  display: 'flex', alignItems: 'center', gap: 16,
                  padding: '14px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer'
                }}>
                  <span style={{ color: 'var(--text-muted)', width: 24, textAlign: 'center', fontWeight: 700 }}>{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '1.05rem' }}>#{t.tag}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{t.count} posts</div>
                  </div>
                  <div style={{
                    width: 100, height: 6, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%', background: 'var(--primary)', borderRadius: 3,
                      width: `${Math.min(100, (t.count / (tags[0]?.count || 1)) * 100)}%`
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
