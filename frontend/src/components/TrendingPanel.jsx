import { useState, useEffect } from 'react'
import { Hash, TrendingUp, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'

export default function TrendingPanel() {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/posts/trending/').then(r => {
      setTags(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <TrendingUp size={18} color="var(--primary)" />
        <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Trending
        </h3>
      </div>
      {loading ? (
        <Loader2 size={20} className="spin" color="var(--primary)" />
      ) : tags.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No trending topics yet</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {tags.slice(0, 10).map((t, i) => (
            <button
              key={t.tag}
              onClick={() => navigate(`/hashtag/${t.tag}`)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 10px', borderRadius: 'var(--radius-md)',
                transition: 'background 0.15s', textAlign: 'left',
                width: '100%', cursor: 'pointer',
                background: 'none', border: 'none',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
              onMouseLeave={e => e.currentTarget.style.background = 'none'}
            >
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', width: 16, textAlign: 'right', flexShrink: 0 }}>{i + 1}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--primary)' }}>#{t.tag}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.count} posts</div>
              </div>
              <Hash size={12} color="var(--text-muted)" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
