import { useState, useEffect, useRef } from 'react'
import { Heart, MessageCircle, Share2, Bookmark, MoreHorizontal, Edit2, Trash2, Flag, Globe, Users, Lock, X, Send, Repeat2, ChevronDown, ChevronUp, Check, BarChart2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import api from '../api/axios'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'

function RichText({ text }) {
  if (!text) return null
  const parts = text.split(/(@\w+|#\w+)/g)
  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith('@'))
          return <Link key={i} to={`/profile/${part.slice(1)}`} style={{ color: 'var(--secondary)', fontWeight: 600 }}>{part}</Link>
        if (part.startsWith('#'))
          return <span key={i} className="hashtag">{part}</span>
        return part
      })}
    </span>
  )
}

function LinkPreview({ preview }) {
  if (!preview?.title) return null
  return (
    <a href={preview.url} target="_blank" rel="noopener noreferrer" className="link-preview">
      {preview.image && <img src={preview.image} alt="" className="link-preview-img" />}
      <div className="link-preview-body">
        <div className="link-preview-domain">{preview.domain}</div>
        <div className="link-preview-title">{preview.title}</div>
        {preview.description && <div className="link-preview-desc">{preview.description}</div>}
      </div>
    </a>
  )
}

// ── Poll ─────────────────────────────────────────────────────────────────────
function PollDisplay({ poll, postId }) {
  const [options, setOptions]   = useState(poll?.options || [])
  const [userVote, setUserVote] = useState(poll?.user_vote || null)
  const [total, setTotal]       = useState(poll?.total_votes || 0)
  const [voting, setVoting]     = useState(false)

  const vote = async (optionId) => {
    if (voting) return
    setVoting(true)
    // Optimistic
    const prev = { options, userVote, total }
    const wasVoted = userVote === optionId
    setUserVote(wasVoted ? null : optionId)
    setTotal(t => wasVoted ? t - 1 : (userVote ? t : t + 1))
    setOptions(opts => opts.map(o => ({
      ...o,
      vote_count: o.id === optionId
        ? o.vote_count + (wasVoted ? -1 : 1)
        : (o.id === userVote ? o.vote_count - 1 : o.vote_count)
    })))
    try {
      const { data } = await api.post(`/posts/${postId}/poll/vote/`, { option_id: optionId })
      setOptions(data.options)
      setUserVote(wasVoted ? null : optionId)
    } catch (e) {
      // Rollback
      setOptions(prev.options)
      setUserVote(prev.userVote)
      setTotal(prev.total)
      toast.error(e.response?.data?.error || 'Vote failed')
    }
    setVoting(false)
  }

  if (!poll) return null
  const hasVoted = userVote !== null

  return (
    <div style={{ padding: '0 16px 12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <BarChart2 size={14} color="var(--primary)" />
        <p style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{poll.question}</p>
      </div>
      {options.map(opt => {
        const pct = total > 0 ? Math.round((opt.vote_count || 0) / total * 100) : 0
        const isMyVote = userVote === opt.id
        return (
          <div
            key={opt.id}
            className={`poll-option${isMyVote ? ' voted' : ''}`}
            onClick={() => vote(opt.id)}
            style={{ cursor: voting ? 'not-allowed' : 'pointer', opacity: voting ? 0.8 : 1 }}
          >
            <div className="poll-bar" style={{ width: hasVoted ? `${pct}%` : '0%' }} />
            <div className="poll-option-text">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {isMyVote && <Check size={12} color="var(--primary)" />}
                {opt.text}
              </span>
              {hasVoted && <span style={{ fontWeight: 700, color: isMyVote ? 'var(--primary)' : 'var(--text-muted)', fontSize: '0.82rem' }}>{pct}%</span>}
            </div>
          </div>
        )
      })}
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 6 }}>
        {total} vote{total !== 1 ? 's' : ''}{' '}
        {poll.closes_at ? `· Ends ${formatDistanceToNow(new Date(poll.closes_at), { addSuffix: true })}` : ''}
      </p>
    </div>
  )
}

// ── Shared post embed ─────────────────────────────────────────────────────────
function SharedPostEmbed({ post }) {
  if (!post) return null
  return (
    <div className="shared-post-embed">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <div className="avatar avatar-xs">
          {post.author?.avatar_url ? <img src={post.author.avatar_url} alt="" /> : <span>{post.author?.username?.[0]?.toUpperCase()}</span>}
        </div>
        <Link to={`/profile/${post.author?.username}`} style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
          {post.author?.username}
        </Link>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          · {post.created_at ? formatDistanceToNow(new Date(post.created_at), { addSuffix: true }) : ''}
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        <RichText text={post.content} />
      </p>
      {post.media?.length > 0 && (
        <img src={post.media[0]} alt="" style={{ width: '100%', maxHeight: 200, objectFit: 'cover', borderRadius: 8, marginTop: 8 }} />
      )}
    </div>
  )
}

// ── Comment row (with edit/delete) ────────────────────────────────────────────
function CommentRow({ comment, currentUser, onDelete, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [text, setText]       = useState(comment.content)
  const [saving, setSaving]   = useState(false)
  const isOwn = currentUser?.id === comment.author?.id

  const saveEdit = async () => {
    if (!text.trim() || text === comment.content) { setEditing(false); return }
    setSaving(true)
    try {
      const { data } = await api.patch(`/posts/comments/${comment.id}/`, { content: text.trim() })
      onUpdate(data)
      setEditing(false)
      toast.success('Comment updated')
    } catch { toast.error('Could not update comment') }
    setSaving(false)
  }

  const del = async () => {
    if (!window.confirm('Delete comment?')) return
    try {
      await api.delete(`/posts/comments/${comment.id}/`)
      onDelete(comment.id)
      toast.success('Comment deleted')
    } catch { toast.error('Could not delete comment') }
  }

  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
      <div className="avatar avatar-sm">
        {comment.author?.avatar_url ? <img src={comment.author.avatar_url} alt="" /> : <span>{comment.author?.username?.[0]?.toUpperCase()}</span>}
      </div>
      <div style={{ flex: 1, background: 'var(--bg-hover)', borderRadius: 10, padding: '8px 12px', position: 'relative' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
            <Link to={`/profile/${comment.author?.username}`} style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)' }}>{comment.author?.username}</Link>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}</span>
            {comment.edited && <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem', fontStyle: 'italic' }}>edited</span>}
          </div>
          {isOwn && (
            <div style={{ display: 'flex', gap: 2 }}>
              <button className="btn btn-ghost" style={{ padding: '2px 4px', fontSize: '0.72rem' }} onClick={() => setEditing(e => !e)}><Edit2 size={11} /></button>
              <button className="btn btn-ghost" style={{ padding: '2px 4px', color: 'var(--danger)' }} onClick={del}><Trash2 size={11} /></button>
            </div>
          )}
        </div>
        {editing ? (
          <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
            <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && saveEdit()} style={{ flex: 1, fontSize: '0.84rem', borderRadius: 6, padding: '4px 8px' }} autoFocus />
            <button className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving}><Check size={12} /></button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setEditing(false); setText(comment.content) }}><X size={12} /></button>
          </div>
        ) : (
          <p style={{ fontSize: '0.86rem', color: 'var(--text-primary)', lineHeight: 1.5 }}><RichText text={comment.content} /></p>
        )}
      </div>
    </div>
  )
}

// ── Comments panel ────────────────────────────────────────────────────────────
function CommentsPanel({ postId, count }) {
  const { user } = useAuthStore()
  const [open, setOpen]       = useState(false)
  const [comments, setComments] = useState([])
  const [text, setText]       = useState('')
  const [loading, setLoading] = useState(false)
  const [posting, setPosting] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    api.get(`/posts/${postId}/comments/`).then(r => {
      setComments(r.data.results || r.data)
      setLoading(false)
    })
  }, [open, postId])

  const submit = async () => {
    if (!text.trim()) return
    setPosting(true)
    try {
      const { data } = await api.post(`/posts/${postId}/comments/`, { content: text.trim() })
      setComments(prev => [...prev, data])
      setText('')
    } catch { toast.error('Could not post comment') }
    setPosting(false)
  }

  return (
    <div style={{ borderTop: '1px solid var(--border)' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', color: 'var(--text-muted)', fontSize: '0.8rem', background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.15s' }}
      >
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {count} comment{count !== 1 ? 's' : ''}
      </button>

      {open && (
        <div style={{ padding: '0 16px 12px' }}>
          {loading ? <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Loading…</p> : (
            comments.map(c => (
              <CommentRow
                key={c.id}
                comment={c}
                currentUser={user}
                onDelete={id => setComments(prev => prev.filter(x => x.id !== id))}
                onUpdate={updated => setComments(prev => prev.map(x => x.id === updated.id ? updated : x))}
              />
            ))
          )}
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            <div className="avatar avatar-sm">
              {user?.avatar_url ? <img src={user.avatar_url} alt="" /> : <span>{user?.username?.[0]?.toUpperCase()}</span>}
            </div>
            <div style={{ flex: 1, display: 'flex', gap: 8 }}>
              <input
                value={text}
                onChange={e => setText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && submit()}
                placeholder="Write a comment…"
                style={{ flex: 1, borderRadius: 20, padding: '8px 14px', fontSize: '0.86rem' }}
              />
              <button className="btn btn-primary btn-icon" onClick={submit} disabled={posting || !text.trim()}>
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Share modal ───────────────────────────────────────────────────────────────
function ShareModal({ post, onClose }) {
  const [caption, setCaption] = useState('')
  const [sharing, setSharing] = useState(false)

  const repost = async () => {
    setSharing(true)
    try {
      await api.post(`/posts/${post.id}/repost/`, { caption })
      toast.success('Reposted!')
      onClose()
    } catch { toast.error('Failed to repost') }
    setSharing(false)
  }

  const copyLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/posts/${post.id}`)
    toast.success('Link copied!')
    onClose()
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--bg-overlay)', zIndex: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }} onClick={onClose}>
      <div className="card" style={{ width: '100%', maxWidth: 480 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontWeight: 700 }}>Share Post</h3>
          <button onClick={onClose} className="btn btn-ghost btn-icon"><X size={18} /></button>
        </div>
        <SharedPostEmbed post={post} />
        <textarea value={caption} onChange={e => setCaption(e.target.value)} placeholder="Add a caption… (optional)" rows={2} style={{ marginTop: 12, resize: 'none' }} />
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={copyLink}>Copy Link</button>
          <button className="btn btn-primary" style={{ flex: 1 }} onClick={repost} disabled={sharing}>
            <Repeat2 size={16} /> {sharing ? 'Reposting…' : 'Repost'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Edit Post Modal ────────────────────────────────────────────────────────────
const POST_EDIT_WINDOW_MS = 30 * 60 * 1000 // 30 min

function EditPostModal({ post, onClose, onUpdate }) {
  const [content, setContent]     = useState(post.content)
  const [visibility, setVisibility] = useState(post.visibility)
  const [saving, setSaving]       = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await api.patch(`/posts/${post.id}/`, { content, visibility })
      onUpdate(data)
      onClose()
      toast.success('Post updated')
    } catch { toast.error('Could not update post') }
    setSaving(false)
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--bg-overlay)', zIndex: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }} onClick={onClose}>
      <div className="card" style={{ width: '100%', maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontWeight: 700 }}>Edit Post</h3>
          <button onClick={onClose} className="btn btn-ghost btn-icon"><X size={18} /></button>
        </div>
        <textarea value={content} onChange={e => setContent(e.target.value)} rows={4} style={{ resize: 'vertical', marginBottom: 12 }} />
        <select value={visibility} onChange={e => setVisibility(e.target.value)} style={{ marginBottom: 16, width: 'auto' }}>
          <option value="public">🌍 Public</option>
          <option value="friends">👥 Friends</option>
          <option value="private">🔒 Private</option>
        </select>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving || !content.trim()}>
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main PostCard ─────────────────────────────────────────────────────────────
export default function PostCard({ post: initialPost, onDelete }) {
  const { user } = useAuthStore()
  const [post, setPost]         = useState(initialPost)
  const [liked, setLiked]       = useState(initialPost.is_liked)
  const [saved, setSaved]       = useState(initialPost.is_saved)
  const [likeCount, setLikeCount] = useState(initialPost.likes_count)
  const [showMenu, setShowMenu] = useState(false)
  const [showShare, setShowShare] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const menuRef = useRef(null)

  const isOwn = user?.id === post.author?.id
  const canEdit = isOwn && (Date.now() - new Date(post.created_at).getTime()) < POST_EDIT_WINDOW_MS

  const VISIBILITY_ICONS = { public: Globe, friends: Users, private: Lock }
  const VisIcon = VISIBILITY_ICONS[post.visibility] || Globe

  useEffect(() => {
    const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const toggleLike = async () => {
    const was = liked
    setLiked(!was); setLikeCount(c => was ? c - 1 : c + 1)
    try { await api.post(`/posts/${post.id}/like/`) }
    catch { setLiked(was); setLikeCount(c => was ? c + 1 : c - 1); toast.error('Action failed') }
  }

  const toggleSave = async () => {
    const was = saved; setSaved(!was)
    try { await api.post(`/posts/${post.id}/save/`); toast(was ? 'Removed from saved' : 'Saved!', { icon: was ? '🗑️' : '🔖' }) }
    catch { setSaved(was) }
  }

  const deletePost = async () => {
    if (!window.confirm('Delete this post?')) return
    try { await api.delete(`/posts/${post.id}/`); onDelete?.(post.id); toast.success('Post deleted') }
    catch { toast.error('Could not delete post') }
  }

  const reportPost = async () => {
    try { await api.post('/reports/', { content_type: 'post', object_id: post.id, reason: 'spam' }); toast.success('Reported. We\'ll review it.') }
    catch { toast.error('Report failed') }
    setShowMenu(false)
  }

  return (
    <article className="post-card fade-in-up">
      {/* Header */}
      <div className="post-header">
        <Link to={`/profile/${post.author?.username}`}>
          <div className="avatar avatar-md">
            {post.author?.avatar_url ? <img src={post.author.avatar_url} alt="" /> : <span>{post.author?.username?.[0]?.toUpperCase()}</span>}
          </div>
        </Link>
        <div className="post-author-info">
          <Link to={`/profile/${post.author?.username}`} className="post-author-name">{post.author?.username}</Link>
          <div className="post-meta" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>{post.created_at ? formatDistanceToNow(new Date(post.created_at), { addSuffix: true }) : ''}</span>
            <VisIcon size={11} />
            {post.edited && <span style={{ fontStyle: 'italic' }}>· edited</span>}
          </div>
        </div>
        <div style={{ position: 'relative' }} ref={menuRef}>
          <button className="btn btn-ghost btn-icon" onClick={() => setShowMenu(m => !m)}>
            <MoreHorizontal size={18} />
          </button>
          {showMenu && (
            <div style={{ position: 'absolute', right: 0, top: '100%', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-lg)', minWidth: 160, zIndex: 100, overflow: 'hidden' }}>
              {isOwn ? (
                <>
                  {canEdit && (
                    <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }} onClick={() => { setShowEdit(true); setShowMenu(false) }}>
                      <Edit2 size={14} /> Edit Post
                    </button>
                  )}
                  <button className="btn btn-ghost" onClick={deletePost} style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0, color: 'var(--danger)' }}>
                    <Trash2 size={14} /> Delete Post
                  </button>
                </>
              ) : (
                <button className="btn btn-ghost" onClick={reportPost} style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0, color: 'var(--warning)' }}>
                  <Flag size={14} /> Report
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="post-content"><RichText text={post.content} /></div>

      {/* Shared post */}
      {post.shared_post && <div style={{ padding: '0 16px 8px' }}><SharedPostEmbed post={post.shared_post} /></div>}

      {/* Poll */}
      {post.poll && <PollDisplay poll={post.poll} postId={post.id} />}

      {/* Link preview */}
      {post.link_preview && !post.media?.length && <div style={{ padding: '0 16px 8px' }}><LinkPreview preview={post.link_preview} /></div>}

      {/* Media */}
      {post.media?.length > 0 && (
        <div className="post-media">
          {post.media_type === 'video' ? (
            <video src={post.media[0]} controls />
          ) : post.media.length === 1 ? (
            <img src={post.media[0]} alt="" loading="lazy" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              {post.media.slice(0, 4).map((url, i) => (
                <img key={i} src={url} alt="" style={{ width: '100%', height: 200, objectFit: 'cover' }} loading="lazy" />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reaction summary */}
      {(likeCount > 0 || post.comments_count > 0) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 16px', color: 'var(--text-muted)', fontSize: '0.78rem', borderTop: '1px solid var(--border)' }}>
          {likeCount > 0 && <span>❤️ {likeCount}</span>}
          {post.shares_count > 0 && <span>{post.shares_count} shares</span>}
        </div>
      )}

      {/* Actions */}
      <div className="post-actions">
        <button className={`post-action-btn ${liked ? 'liked' : ''}`} onClick={toggleLike}>
          <Heart size={18} fill={liked ? '#ef4444' : 'none'} /> {likeCount > 0 ? likeCount : ''}
        </button>
        <button className="post-action-btn">
          <MessageCircle size={18} /> {post.comments_count || ''}
        </button>
        <button className="post-action-btn" onClick={() => setShowShare(true)}>
          <Share2 size={18} /> {post.shares_count > 0 ? post.shares_count : ''}
        </button>
        <button className={`post-action-btn ${saved ? 'saved' : ''}`} onClick={toggleSave} style={{ marginLeft: 'auto' }}>
          <Bookmark size={18} fill={saved ? 'currentColor' : 'none'} />
        </button>
      </div>

      {/* Comments */}
      <CommentsPanel postId={post.id} count={post.comments_count} />

      {/* Modals */}
      {showShare && <ShareModal post={post} onClose={() => setShowShare(false)} />}
      {showEdit  && <EditPostModal post={post} onClose={() => setShowEdit(false)} onUpdate={data => setPost(p => ({ ...p, ...data }))} />}
    </article>
  )
}
