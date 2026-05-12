import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, Zap, Check } from 'lucide-react'
import useAuthStore from '../store/authStore'
import s from './Auth.module.css'

function strength(pw) {
  let score = 0
  if (pw.length >= 8)  score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  return score
}

const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong']
const strengthColor = ['', '#f87171', '#fbbf24', '#60a5fa', '#3ecf8e']

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, loading, error, clearError } = useAuthStore()
  const [form, setForm] = useState({ username: '', email: '', password: '', password2: '' })
  const [showPw, setShowPw] = useState(false)
  const [done, setDone] = useState(false)

  const set = (k, v) => { clearError(); setForm(f => ({ ...f, [k]: v })) }
  const pwStrength = strength(form.password)
  const pwMismatch = form.password2.length > 0 && form.password !== form.password2

  const submit = async (e) => {
    e.preventDefault()
    if (pwMismatch) return
    const ok = await register(form)
    if (ok) setDone(true)
  }

  if (done) return (
    <div className={s.shell}>
      <div className={s.visual}>
        <div className={s.mesh} />
        <div className={s.visualContent}>
          <div className={s.wordmark}><Zap size={18} strokeWidth={2.5} />MindConnect</div>
          <h1 className={s.headline}>You're in.<br /><span className={s.accent}>Let's chat.</span></h1>
        </div>
      </div>
      <div className={s.panel}>
        <div className={s.panelInner}>
          <div className={s.successWrap}>
            <div className={s.successRing}>
              <Check size={28} strokeWidth={2.5} />
            </div>
            <h2 className={s.formTitle}>Account created</h2>
            <p className={s.formSub}>Your account is ready. Sign in to start.</p>
            <button className={s.submitBtn} onClick={() => navigate('/login')}>
              <span>Go to Sign in</span><ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className={s.shell}>
      <div className={s.visual}>
        <div className={s.mesh} />
        <div className={s.visualContent}>
          <div className={s.wordmark}><Zap size={18} strokeWidth={2.5} />MindConnect</div>
          <h1 className={s.headline}>Start for<br /><span className={s.accent}>free today.</span></h1>
          <p className={s.sub}>No credit card. No limits. Just conversations.</p>
          <div className={s.perks}>
            {['Unlimited messages','Group chats up to 500 members','File & media sharing','Real-time presence'].map(p => (
              <div key={p} className={s.perk}>
                <span className={s.perkCheck}><Check size={11} strokeWidth={3} /></span>
                {p}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={s.panel}>
        <div className={s.panelInner}>
          <div className={s.formHead}>
            <h2 className={s.formTitle}>Create account</h2>
            <p className={s.formSub}>Takes less than a minute</p>
          </div>

          {error && (
            <div className={s.errorBanner}>
              <span className={s.errorDot} />
              {error}
            </div>
          )}

          <form onSubmit={submit} className={s.form}>
            <div className={s.fieldRow}>
              <div className={s.field}>
                <label className={s.label}>Username</label>
                <div className={s.inputWrap}>
                  <User size={15} className={s.inputIcon} />
                  <input className={s.input} type="text" placeholder="johndoe"
                    value={form.username} onChange={e => set('username', e.target.value)} required autoFocus />
                </div>
              </div>
              <div className={s.field}>
                <label className={s.label}>Email</label>
                <div className={s.inputWrap}>
                  <Mail size={15} className={s.inputIcon} />
                  <input className={s.input} type="email" placeholder="you@example.com"
                    value={form.email} onChange={e => set('email', e.target.value)} required />
                </div>
              </div>
            </div>

            <div className={s.field}>
              <label className={s.label}>Password</label>
              <div className={s.inputWrap}>
                <Lock size={15} className={s.inputIcon} />
                <input className={s.input} type={showPw ? 'text' : 'password'} placeholder="Min. 8 characters"
                  value={form.password} onChange={e => set('password', e.target.value)} required />
                <button type="button" className={s.eyeBtn} onClick={() => setShowPw(v => !v)} tabIndex={-1}>
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {form.password.length > 0 && (
                <div className={s.strengthWrap}>
                  <div className={s.strengthBar}>
                    {[1,2,3,4].map(i => (
                      <div key={i} className={s.strengthSeg}
                        style={{ background: i <= pwStrength ? strengthColor[pwStrength] : 'rgba(255,255,255,.08)' }} />
                    ))}
                  </div>
                  <span className={s.strengthLabel} style={{ color: strengthColor[pwStrength] }}>
                    {strengthLabel[pwStrength]}
                  </span>
                </div>
              )}
            </div>

            <div className={s.field}>
              <label className={s.label}>Confirm password</label>
              <div className={[s.inputWrap, pwMismatch ? s.inputError : ''].join(' ')}>
                <Lock size={15} className={s.inputIcon} />
                <input className={s.input} type={showPw ? 'text' : 'password'} placeholder="Repeat password"
                  value={form.password2} onChange={e => set('password2', e.target.value)} required />
              </div>
              {pwMismatch && <span className={s.fieldError}>Passwords don't match</span>}
            </div>

            <button type="submit" className={s.submitBtn} disabled={loading || pwMismatch}>
              {loading
                ? <span className={s.spinner} />
                : <><span>Create account</span><ArrowRight size={16} /></>
              }
            </button>
          </form>

          <p className={s.switchLine}>
            Already have an account?{' '}
            <Link to="/login" className={s.switchLink}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
