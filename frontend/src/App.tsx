import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'

import { createChat, listChatMessages, listChats, sendChatMessage, type ChatMessage, type ChatThread } from './lib/api'
import { useAuth } from './lib/auth'
import './App.css'

type AuthMode = 'sign-in' | 'sign-up'

function AuthPage({ mode }: { mode: AuthMode }) {
  const { session, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (session) return <Navigate to="/" replace />

  const isSignUp = mode === 'sign-up'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)

    try {
      if (isSignUp) {
        const hasSession = await signUp(email, password)
        if (hasSession) navigate('/')
        else setMessage('Check your email to confirm your account before signing in.')
      } else {
        await signIn(email, password)
        navigate('/')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <p className="eyebrow">DRIFTWOOD CAPITAL</p>
        <h1>{isSignUp ? 'Create your analyst account' : 'Welcome back'}</h1>
        <p className="auth-copy">
          {isSignUp ? 'Use your email to join the research workspace.' : 'Sign in to continue your research workspace.'}
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} autoComplete={isSignUp ? 'new-password' : 'current-password'} />
          </label>
          {error && <p className="form-error">{error}</p>}
          {message && <p className="form-message">{message}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Working...' : isSignUp ? 'Create account' : 'Sign in'}
          </button>
        </form>
        <p className="auth-switch">
          {isSignUp ? 'Already have an account?' : 'Need an account?'}{' '}
          <button type="button" className="link-button" onClick={() => navigate(isSignUp ? '/login' : '/signup')}>
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>
      </section>
    </main>
  )
}

function ProtectedHome() {
  const { backendUser, signOut } = useAuth()
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void listChats()
      .then((nextThreads) => {
        setThreads(nextThreads)
        setSelectedThreadId((current) => current ?? nextThreads[0]?.id ?? null)
      })
      .catch(() => setError('Could not load your conversations.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedThreadId) {
      return
    }

    void listChatMessages(selectedThreadId)
      .then(setMessages)
      .catch(() => setError('Could not load this conversation.'))
  }, [selectedThreadId])

  async function handleNewChat() {
    setError('')
    try {
      const thread = await createChat()
      setThreads((current) => [thread, ...current])
      setSelectedThreadId(thread.id)
      setMessages([])
    } catch {
      setError('Could not create a conversation.')
    }
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!draft.trim() || !selectedThreadId || sending) return

    setSending(true)
    setError('')
    try {
      const nextMessages = await sendChatMessage(selectedThreadId, draft.trim())
      setMessages((current) => [...current, ...nextMessages])
      setDraft('')
    } catch {
      setError('Could not send your message.')
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="workspace-page">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">DRIFTWOOD CAPITAL</p>
          <h1>Research workspace</h1>
          <p>{backendUser ? `Authenticated as ${backendUser.email}` : 'Verifying your session...'}</p>
        </div>
        <button type="button" onClick={() => void signOut().then(() => navigate('/login'))}>
          Sign out
        </button>
      </div>
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="sidebar-heading">
            <h2>Conversations</h2>
            <button type="button" onClick={() => void handleNewChat()}>New</button>
          </div>
          {threads.map((thread) => (
            <button
              className={`thread-item ${thread.id === selectedThreadId ? 'selected' : ''}`}
              key={thread.id}
              type="button"
              onClick={() => setSelectedThreadId(thread.id)}
            >
              {thread.title}
            </button>
          ))}
          {!loading && threads.length === 0 && <p className="empty-state">Start a conversation.</p>}
        </aside>
        <section className="chat-panel">
          <div className="message-feed">
            {messages.length === 0 && <p className="empty-state">Ask about the SEC filing corpus to begin.</p>}
            {messages.map((message) => (
              <article className={`message ${message.role.toLowerCase()}`} key={message.id}>
                <p className="message-role">{message.role === 'USER' ? 'You' : 'Assistant'}</p>
                <p>{message.content}</p>
              </article>
            ))}
          </div>
          {error && <p className="form-error chat-error">{error}</p>}
          <form className="message-composer" onSubmit={handleSend}>
            <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask a research question" disabled={!selectedThreadId || sending} />
            <button type="submit" disabled={!selectedThreadId || sending || !draft.trim()}>{sending ? 'Sending...' : 'Send'}</button>
          </form>
        </section>
      </div>
    </main>
  )
}

function ProtectedRoute() {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) return <main className="loading-page">Checking session...</main>
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />
  return <ProtectedHome />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="sign-in" />} />
      <Route path="/signup" element={<AuthPage mode="sign-up" />} />
      <Route path="/" element={<ProtectedRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
