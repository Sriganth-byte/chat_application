import { useEffect, useState } from 'react'
import { Activity, BarChart3, FileText, Flag, Loader2, Plus, RefreshCw, Shield, Trash2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/axios'

const TABS = [
  { key: 'overview', label: 'Overview', icon: BarChart3 },
  { key: 'users', label: 'Users', icon: Users },
  { key: 'posts', label: 'Posts', icon: FileText },
  { key: 'reports', label: 'Reports', icon: Flag },
  { key: 'audit', label: 'Audit Log', icon: Activity },
]

export default function AdminManagement() {
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState(null)
  const [users, setUsers] = useState([])
  const [posts, setPosts] = useState([])
  const [reports, setReports] = useState([])
  const [audit, setAudit] = useState([])
  const [query, setQuery] = useState('')
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', is_staff: false })
  const [newPost, setNewPost] = useState({ content: '', visibility: 'public', status: 'published' })

  const loadAll = async () => {
    setLoading(true)
    try {
      const [overviewRes, usersRes, postsRes, reportsRes, auditRes] = await Promise.all([
        api.get('/admin-dashboard/dashboard/'),
        api.get('/admin-dashboard/users/'),
        api.get('/admin-dashboard/posts/'),
        api.get('/admin-dashboard/reports/'),
        api.get('/admin-dashboard/audit/'),
      ])
      setOverview(overviewRes.data)
      setUsers(usersRes.data)
      setPosts(postsRes.data)
      setReports(reportsRes.data)
      setAudit(auditRes.data)
    } catch (e) {
      toast.error(e.response?.status === 403 ? 'Admin access required' : 'Could not load admin data')
    }
    setLoading(false)
  }

  useEffect(() => { loadAll() }, [])

  const createUser = async () => {
    if (!newUser.username || !newUser.email) return toast.error('Username and email are required')
    try {
      const { data } = await api.post('/admin-dashboard/users/', newUser)
      setUsers(u => [data, ...u])
      setNewUser({ username: '', email: '', password: '', is_staff: false })
      toast.success('User created')
    } catch (e) { toast.error(e.response?.data?.error || 'Could not create user') }
  }

  const patchUser = async (id, patch) => {
    try {
      const { data } = await api.patch(`/admin-dashboard/users/${id}/`, patch)
      setUsers(items => items.map(u => u.id === id ? data : u))
      toast.success('User updated')
    } catch { toast.error('Could not update user') }
  }

  const deleteUser = async (id) => {
    if (!window.confirm('Delete this user account?')) return
    try {
      await api.delete(`/admin-dashboard/users/${id}/`)
      setUsers(items => items.filter(u => u.id !== id))
      toast.success('User deleted')
    } catch (e) { toast.error(e.response?.data?.error || 'Could not delete user') }
  }

  const createPost = async () => {
    if (!newPost.content.trim()) return toast.error('Post content is required')
    try {
      const { data } = await api.post('/admin-dashboard/posts/', newPost)
      setPosts(p => [data, ...p])
      setNewPost({ content: '', visibility: 'public', status: 'published' })
      toast.success('Post created')
    } catch { toast.error('Could not create post') }
  }

  const patchPost = async (id, patch) => {
    try {
      const { data } = await api.patch(`/admin-dashboard/posts/${id}/`, patch)
      setPosts(items => items.map(p => p.id === id ? data : p))
      toast.success('Post updated')
    } catch { toast.error('Could not update post') }
  }

  const deletePost = async (id) => {
    if (!window.confirm('Delete this post?')) return
    try {
      await api.delete(`/admin-dashboard/posts/${id}/`)
      setPosts(items => items.filter(p => p.id !== id))
      toast.success('Post deleted')
    } catch { toast.error('Could not delete post') }
  }

  const resolveReport = async (id, status, reviewer_note = '') => {
    try {
      const { data } = await api.patch(`/admin-dashboard/reports/${id}/`, { status, reviewer_note })
      setReports(items => items.map(r => r.id === id ? data : r))
      toast.success('Report updated')
    } catch { toast.error('Could not update report') }
  }

  const filteredUsers = users.filter(u => `${u.username} ${u.email}`.toLowerCase().includes(query.toLowerCase()))
  const filteredPosts = posts.filter(p => `${p.content} ${p.author_username}`.toLowerCase().includes(query.toLowerCase()))

  return (
    <div className="admin-page">
      <div className="admin-head">
        <div>
          <div className="admin-kicker"><Shield size={15} /> Admin Console</div>
          <h1>System & Application Management</h1>
          <p>Manage users, content, moderation queues, and audit activity from one operational dashboard.</p>
        </div>
        <button className="btn btn-secondary" onClick={loadAll}><RefreshCw size={16} /> Refresh</button>
      </div>

      <div className="admin-tabs">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="admin-loading"><Loader2 className="spin" /> Loading admin console...</div>
      ) : (
        <>
          {tab === 'overview' && <Overview overview={overview} />}
          {tab === 'users' && (
            <UsersPanel users={filteredUsers} query={query} setQuery={setQuery} newUser={newUser} setNewUser={setNewUser} createUser={createUser} patchUser={patchUser} deleteUser={deleteUser} />
          )}
          {tab === 'posts' && (
            <PostsPanel posts={filteredPosts} query={query} setQuery={setQuery} newPost={newPost} setNewPost={setNewPost} createPost={createPost} patchPost={patchPost} deletePost={deletePost} />
          )}
          {tab === 'reports' && <ReportsPanel reports={reports} resolveReport={resolveReport} />}
          {tab === 'audit' && <AuditPanel audit={audit} />}
        </>
      )}
    </div>
  )
}

function Overview({ overview }) {
  const cards = [
    ['Users', overview?.users?.total, `${overview?.users?.online || 0} online`],
    ['Posts', overview?.content?.posts, `${overview?.content?.published_posts || 0} published`],
    ['Messages', overview?.content?.messages, `${overview?.content?.rooms || 0} rooms`],
    ['Reports', overview?.moderation?.pending_reports, `${overview?.moderation?.auto_flagged || 0} auto flagged`],
  ]
  return (
    <div className="admin-stack">
      <div className="admin-stat-grid">
        {cards.map(([label, value, sub]) => <div className="admin-stat" key={label}><span>{label}</span><strong>{value ?? 0}</strong><small>{sub}</small></div>)}
      </div>
      <div className="admin-two-col">
        <MiniList title="Recent Users" items={overview?.recent_users || []} render={u => <><strong>{u.username}</strong><span>{u.email}</span></>} />
        <MiniList title="Recent Reports" items={overview?.recent_reports || []} render={r => <><strong>{r.reason}</strong><span>{r.target_type} #{r.target_id} · {r.status}</span></>} />
      </div>
    </div>
  )
}

function MiniList({ title, items, render }) {
  return <div className="card admin-card"><h3>{title}</h3>{items.length ? items.map(item => <div className="admin-mini-row" key={item.id}>{render(item)}</div>) : <p className="admin-muted">No data yet.</p>}</div>
}

function UsersPanel({ users, query, setQuery, newUser, setNewUser, createUser, patchUser, deleteUser }) {
  return (
    <div className="admin-stack">
      <div className="card admin-card admin-form-grid">
        <input placeholder="Username" value={newUser.username} onChange={e => setNewUser(s => ({ ...s, username: e.target.value }))} />
        <input placeholder="Email" type="email" value={newUser.email} onChange={e => setNewUser(s => ({ ...s, email: e.target.value }))} />
        <input placeholder="Temporary password" type="password" value={newUser.password} onChange={e => setNewUser(s => ({ ...s, password: e.target.value }))} />
        <label className="admin-check"><input type="checkbox" checked={newUser.is_staff} onChange={e => setNewUser(s => ({ ...s, is_staff: e.target.checked }))} /> Staff</label>
        <button className="btn btn-primary" onClick={createUser}><Plus size={16} /> Create User</button>
      </div>
      <input className="admin-search" placeholder="Search users..." value={query} onChange={e => setQuery(e.target.value)} />
      <div className="card admin-card admin-table">
        {users.map(u => <div className="admin-row" key={u.id}>
          <div><strong>{u.username}</strong><span>{u.email}</span></div>
          <button onClick={() => patchUser(u.id, { is_active: !u.is_active })}>{u.is_active ? 'Deactivate' : 'Activate'}</button>
          <button onClick={() => patchUser(u.id, { is_staff: !u.is_staff })}>{u.is_staff ? 'Remove Staff' : 'Make Staff'}</button>
          <button onClick={() => patchUser(u.id, { is_verified: !u.is_verified })}>{u.is_verified ? 'Unverify' : 'Verify'}</button>
          <button className="danger" onClick={() => deleteUser(u.id)}><Trash2 size={14} /></button>
        </div>)}
      </div>
    </div>
  )
}

function PostsPanel({ posts, query, setQuery, newPost, setNewPost, createPost, patchPost, deletePost }) {
  return (
    <div className="admin-stack">
      <div className="card admin-card admin-post-create">
        <textarea placeholder="Create an admin/system post..." value={newPost.content} onChange={e => setNewPost(s => ({ ...s, content: e.target.value }))} rows={3} />
        <select value={newPost.visibility} onChange={e => setNewPost(s => ({ ...s, visibility: e.target.value }))}><option value="public">Public</option><option value="friends">Friends</option><option value="private">Private</option></select>
        <select value={newPost.status} onChange={e => setNewPost(s => ({ ...s, status: e.target.value }))}><option value="published">Published</option><option value="draft">Draft</option></select>
        <button className="btn btn-primary" onClick={createPost}><Plus size={16} /> Create Post</button>
      </div>
      <input className="admin-search" placeholder="Search posts..." value={query} onChange={e => setQuery(e.target.value)} />
      <div className="card admin-card admin-table">
        {posts.map(p => <div className="admin-row" key={p.id}>
          <div><strong>{p.author_username}</strong><span>{p.content || '(No text)'}</span></div>
          <select value={p.status} onChange={e => patchPost(p.id, { status: e.target.value })}><option value="published">Published</option><option value="draft">Draft</option><option value="scheduled">Scheduled</option></select>
          <button onClick={() => patchPost(p.id, { is_pinned: !p.is_pinned })}>{p.is_pinned ? 'Unpin' : 'Pin'}</button>
          <button className="danger" onClick={() => deletePost(p.id)}><Trash2 size={14} /></button>
        </div>)}
      </div>
    </div>
  )
}

function ReportsPanel({ reports, resolveReport }) {
  return <div className="card admin-card admin-table">{reports.map(r => <ReportRow key={r.id} report={r} resolveReport={resolveReport} />)}</div>
}

function ReportRow({ report, resolveReport }) {
  const [note, setNote] = useState(report.reviewer_note || '')
  return <div className="admin-row report-row">
    <div><strong>{report.reason} · {report.target_type} #{report.target_id}</strong><span>By {report.reporter_username} · {report.status}</span></div>
    <input placeholder="Reviewer note" value={note} onChange={e => setNote(e.target.value)} />
    <button onClick={() => resolveReport(report.id, 'reviewing', note)}>Reviewing</button>
    <button onClick={() => resolveReport(report.id, 'resolved_action', note)}>Action Taken</button>
    <button onClick={() => resolveReport(report.id, 'resolved_dismissed', note)}>Dismiss</button>
  </div>
}

function AuditPanel({ audit }) {
  return <div className="card admin-card admin-table">{audit.map(a => <div className="admin-row" key={a.id}><div><strong>{a.action}</strong><span>{a.actor} · {a.target_type} #{a.target_id || '-'} · {new Date(a.created_at).toLocaleString()}</span></div></div>)}</div>
}
