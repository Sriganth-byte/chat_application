import { useState, useEffect } from 'react'
import { Heart, Eye, MessageCircle, Share2, Bookmark, BarChart2, Users, ArrowUp, ArrowDown, Star } from 'lucide-react'
import api from '../api/axios'
import { formatDistanceToNow } from 'date-fns'
import { motion } from 'framer-motion'

function StatCard({ icon: Icon, label, value, change, color }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="card" style={{ flex: '1 1 160px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={16} color={color} />
        </div>
        {change !== undefined && (
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: change >= 0 ? '#10b981' : '#ef4444', background: change >= 0 ? '#10b98118' : '#ef444418', padding: '2px 8px', borderRadius: 999, display: 'flex', alignItems: 'center', gap: 2 }}>
            {change >= 0 ? <ArrowUp size={10} /> : <ArrowDown size={10} />} {Math.abs(change)}
          </span>
        )}
      </div>
      <div style={{ fontSize: '1.7rem', fontWeight: 800 }}>{typeof value === 'number' ? value.toLocaleString() : value}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 3 }}>{label}</div>
    </motion.div>
  )
}

function PostDetailModal({ postId, onClose }) {
  const [data, setData] = useState(null)
  useEffect(() => {
    api.get(`/posts/${postId}/analytics/`).then(r => setData(r.data))
  }, [postId])

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'var(--bg-overlay)', zIndex: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div className="card" style={{ width: '100%', maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontWeight: 700 }}>Post Analytics</h3>
          <button onClick={onClose} className="btn btn-ghost btn-icon">✕</button>
        </div>
        {!data ? <p style={{ color: 'var(--text-muted)' }}>Loading…</p> : (
          <>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
              {[
                { l: 'Views', v: data.summary.views, c: '#3b82f6' },
                { l: 'Likes', v: data.summary.likes, c: '#ef4444' },
                { l: 'Comments', v: data.summary.comments, c: '#10b981' },
                { l: 'Saves', v: data.summary.saves, c: '#f59e0b' },
              ].map(s => (
                <div key={s.l} style={{ flex: '1 1 80px', textAlign: 'center', padding: '10px 8px', background: 'var(--bg-hover)', borderRadius: 10 }}>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: s.c }}>{s.v}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{s.l}</div>
                </div>
              ))}
            </div>
            <div style={{ padding: 12, background: 'var(--bg-hover)', borderRadius: 10 }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Engagement Rate</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary)' }}>{data.summary.engagement_rate}%</div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedPost, setSelectedPost] = useState(null)

  useEffect(() => {
    api.get('/auth/analytics/').then(r => { setStats(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: 24 }}>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[1,2,3,4].map(i => <div key={i} className="card" style={{ flex: '1 1 160px', height: 100, background: 'var(--bg-hover)' }} />)}
      </div>
    </div>
  )

  if (!stats) return <p style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Could not load analytics.</p>

  const { summary, trends, top_posts } = stats

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '24px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0 }}>Analytics</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '4px 0 0' }}>Your performance overview</p>
        </div>
        <BarChart2 size={26} color="var(--primary)" />
      </div>

      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 20 }}>
        <StatCard icon={Heart} label="Total Likes" value={summary.total_likes} color="#ef4444" />
        <StatCard icon={MessageCircle} label="Comments" value={summary.total_comments} color="#10b981" />
        <StatCard icon={Bookmark} label="Saves" value={summary.total_saves} color="#f59e0b" />
        <StatCard icon={Users} label="Followers" value={summary.followers} change={trends.posts_change} color="#8b5cf6" />
      </div>

      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 14 }}>Last 7 Days</h3>
          <div style={{ display: 'flex', gap: 20 }}>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{trends.posts_last_7_days}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Posts</div>
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{trends.likes_last_7_days}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Likes</div>
            </div>
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 14 }}>Account</h3>
          <div style={{ display: 'flex', gap: 20 }}>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{summary.total_posts}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Posts</div>
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{summary.following}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Following</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Star size={15} color="#f59e0b" /> Top Posts
        </h3>
        {top_posts.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No posts yet. Start posting!</p>
        ) : (
          top_posts.map((post, i) => (
            <div key={post.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '10px 0', borderBottom: i < top_posts.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: i === 0 ? '#f59e0b' : 'var(--bg-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, color: i === 0 ? 'white' : 'var(--text-muted)', flexShrink: 0 }}>{i+1}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: '0.84rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{post.content || '(No text)'}</p>
                <div style={{ display: 'flex', gap: 10, marginTop: 3 }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>❤️ {post.likes_count}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>👁 {post.views_count}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{formatDistanceToNow(new Date(post.created_at), { addSuffix: true })}</span>
                </div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelectedPost(post.id)}>
                <BarChart2 size={13} />
              </button>
            </div>
          ))
        )}
      </div>
      {selectedPost && <PostDetailModal postId={selectedPost} onClose={() => setSelectedPost(null)} />}
    </div>
  )
}
