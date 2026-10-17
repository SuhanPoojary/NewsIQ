
import { useState } from 'react'
import axios from 'axios'
import { Newspaper, ArrowRight, Check, Eye, EyeOff } from 'lucide-react'
import './AuthPage.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011'

const topics = [
  'Technology',
  'Business',
  'Science',
  'World',
  'Sports',
  'Other',
]

export default function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState('register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [interests, setInterests] = useState(['Technology', 'Business'])
  const [customInterest, setCustomInterest] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isRegister = mode === 'register'

  const toggleInterest = topic => {
    setInterests(current =>
      current.includes(topic)
        ? current.filter(item => item !== topic)
        : [...current, topic]
    )
  }

  const addCustomInterest = () => {
    const topic = customInterest.trim()

    if (!topic) return

    const exists = interests.some(
      item => item.toLowerCase() === topic.toLowerCase()
    )

    if (exists) {
      setError('This interest is already selected.')
      return
    }

    setInterests(current => [...current, topic])
    setCustomInterest('')
    setError('')
  }

  const handleSubmit = async event => {
    event.preventDefault()
    setError('')

    if (isRegister && interests.length === 0) {
      setError('Choose at least one topic for your feed.')
      return
    }

    setLoading(true)

    try {
      const endpoint = isRegister ? '/api/register' : '/api/login'
      const payload = isRegister
        ? { email, password, categories: interests }
        : { email, password }

      const response = await axios.post(`${API_URL}${endpoint}`, payload)
      const session = {
        token: response.data.access_token,
        user: response.data.user,
        categories: response.data.categories || ['Technology', 'Business'],
      }

      sessionStorage.setItem('newsiq-session', JSON.stringify(session))
      onAuthenticated(session)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Could not connect to NewsIQ. Check that the backend is running.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-editorial">
        <header className="auth-masthead">
          <div className="auth-brand-mark"><Newspaper size={22} /></div>
          <span>NewsIQ</span>
          <span className="masthead-edition">THE DAILY BRIEF</span>
        </header>

        <div className="editorial-copy">
          <p className="editorial-kicker">
            <span /> A CLEARER VIEW OF THE WORLD
          </p>
          <h1>
            The world<br />
            moves fast.<br />
            <em>Stay ahead.</em>
          </h1>
          <p className="editorial-description">
            The stories that matter, from the sources that report them.
            Your interests, your reading list, one considered space.
          </p>
        </div>

        <div className="editorial-story">
          <div className="story-rule" />
          <div>
            <span className="story-label">THE NEWSIQ PROMISE</span>
            <p>Less noise. Better context. A feed that feels like yours.</p>
          </div>
        </div>

        <footer className="editorial-footer">
          <span>INDEPENDENT THINKING STARTS HERE</span>
          <span>VOL. 01 — 2026</span>
        </footer>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <div className="auth-mobile-brand">
            <Newspaper size={21} /> NewsIQ
          </div>

          <div className="auth-topline">
            <span>{isRegister ? 'YOUR PERSONAL EDITION' : 'WELCOME BACK'}</span>
            <span className="auth-step">{isRegister ? '01 / 02' : 'SIGN IN'}</span>
          </div>

          <h2>{isRegister ? 'Make it yours.' : 'Good to have you back.'}</h2>
          <p className="auth-subtitle">
            {isRegister
              ? 'Build a reading space around what you care about.'
              : 'Sign in to pick up where your curiosity left off.'}
          </p>

          <form onSubmit={handleSubmit}>
            <label className="auth-label" htmlFor="auth-email">EMAIL ADDRESS</label>
            <input
              id="auth-email"
              className="auth-input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              required
            />

            <label className="auth-label" htmlFor="auth-password">PASSWORD</label>
            <div className="password-field">
              <input
                id="auth-password"
                className="auth-input"
                type={showPassword ? 'text' : 'password'}
                placeholder={isRegister ? 'At least 8 characters' : 'Your password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                minLength={isRegister ? 8 : undefined}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(value => !value)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>

            {isRegister && (
              <div className="interest-section">
                <div className="interest-heading">
                  <div>
                    <span className="auth-label">YOUR READING INTERESTS</span>
                    <p>Choose the topics you want to see first.</p>
                  </div>
                  <span className="interest-count">{interests.length} selected</span>
                </div>

                <div className="interest-options">
                  {topics.map(topic => {
                    const selected = interests.includes(topic)
                    return (
                      <button
                        type="button"
                        key={topic}
                        className={`interest-option ${selected ? 'selected' : ''}`}
                        onClick={() => toggleInterest(topic)}
                        aria-pressed={selected}
                      >
                        <span className="interest-check">
                          {selected && <Check size={13} />}
                        </span>
                        {topic}
                      </button>
                    )
                  })}
                </div>

                <div className="custom-interest">
                  <label className="auth-label" htmlFor="custom-interest">
                    ADD YOUR OWN TOPIC
                  </label>

                  <div className="password-field">
                    <input
                      id="custom-interest"
                      className="auth-input"
                      type="text"
                      placeholder="e.g. Artificial Intelligence"
                      value={customInterest}
                      onChange={e => setCustomInterest(e.target.value)}
                      maxLength={40}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          addCustomInterest()
                        }
                      }}
                    />

                    <button
                      type="button"
                      className="password-toggle"
                      onClick={addCustomInterest}
                    >
                      Add
                    </button>
                  </div>

                  <div className="interest-options">
                    {interests
                      .filter(topic => !topics.includes(topic))
                      .map(topic => (
                        <button
                          type="button"
                          key={topic}
                          className="interest-option selected"
                          onClick={() =>
                            setInterests(current =>
                              current.filter(item => item !== topic)
                            )
                          }
                        >
                          <span className="interest-check">
                            <Check size={13} />
                          </span>
                          {topic} ×
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            )}

            {error && <p className="auth-error" role="alert">{error}</p>}

            <button className="auth-submit" type="submit" disabled={loading}>
              {loading
                ? 'One moment...'
                : isRegister ? 'Create my edition' : 'Sign in to NewsIQ'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="auth-switch">
            {isRegister ? 'Already have an account?' : 'New to NewsIQ?'}
            <button
              type="button"
              onClick={() => {
                setMode(isRegister ? 'login' : 'register')
                setError('')
              }}
            >
              {isRegister ? 'Sign in' : 'Create an account'}
            </button>
          </div>

          <p className="auth-privacy">
            Your interests shape your feed. You can change them later.
          </p>
        </div>
      </section>
    </main>
  )
}
