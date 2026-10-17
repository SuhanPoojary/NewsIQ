
import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  Activity, Bookmark, ChevronRight, Cpu, Globe2, Home,
  Menu, Search, Sparkles, TrendingUp, Zap, Newspaper,
  Clock3, ArrowUpRight, RefreshCw
} from 'lucide-react'
import './App.css'

const API_URL = 'http://localhost:8001'

const categories = [
  'All News', 'Technology', 'Business', 'Science', 'World', 'Sports'
]

function normalizeArticle(article, index) {
  const description = article.description || 'No description is available for this story.'

  const cleanDescription = description
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim()

  return {
    id: article.url || article.id || `${article.title}-${index}`,
    title: article.title || 'Untitled story',
    description: cleanDescription,
    source: article.source || 'News source',
    category: article.category || 'World',
    time: article.published || '',
    url: article.url || '',
    image: article.image || null,
    color: '#e8e7ff',
    tag: (article.category || 'NEWS').toUpperCase(),
    // Placeholder until the actual AI summarization pipeline is implemented.
    summary: cleanDescription,
  }
}

function App() {
  const [activeCategory, setActiveCategory] = useState('All News')
  const [query, setQuery] = useState('')
  const [bookmarks, setBookmarks] = useState([])
  const [savedArticles, setSavedArticles] = useState([])
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [bookmarkError, setBookmarkError] = useState('')
  const [savedOnly, setSavedOnly] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [showSummary, setShowSummary] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState('')

  // Live news API state
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadNews() {
      setLoading(true)
      setApiError('')

      try {
        const response = await axios.get(`${API_URL}/api/news`, {
          timeout: 20000,
        })

        if (!cancelled) {
          const incoming = response.data.articles || []
          setArticles(incoming.map(normalizeArticle))
        }
      } catch (error) {
        if (!cancelled) {
          setApiError(
            error.response
              ? `News API returned status ${error.response.status}.`
              : 'Could not connect to NewsIQ. Check that the backend is running on port 8000.'
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadNews()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
  let cancelled = false

  async function loadBookmarks() {
    setBookmarkLoading(true)
    setBookmarkError('')

    try {
      const response = await axios.get(`${API_URL}/api/bookmarks`)

      if (!cancelled) {
        const saved = response.data || []
        setSavedArticles(saved)
        setBookmarks(saved.map(item => item.article_url))
      }
    } catch (error) {
      if (!cancelled) {
        setBookmarkError('Could not load saved articles from the database.')
      }
    } finally {
      if (!cancelled) setBookmarkLoading(false)
    }
  }

  loadBookmarks()

  return () => {
    cancelled = true
  }
}, [])
  
const displayArticles = savedOnly
  ? savedArticles.map((item, index) =>
      normalizeArticle(
        {
          id: item.id,
          url: item.article_url,
          title: item.title,
          description: item.description,
          source: item.source,
          category: item.category,
          published: item.created_at
            ? new Date(item.created_at).toLocaleDateString()
            : '',
        },
        index
      )
    )
  : articles

const filtered = displayArticles.filter(article => {
  const matchesCategory =
    activeCategory === 'All News' ||
    article.category.toLowerCase() === activeCategory.toLowerCase()

  const matchesSearch =
    `${article.title} ${article.description} ${article.source}`
      .toLowerCase()
      .includes(query.toLowerCase())

  return matchesCategory && matchesSearch
})


  const toggleBookmark = async article => {
  const existing = savedArticles.find(
    item => item.article_url === article.url
  )

  setBookmarkError('')

  try {
    if (existing) {
      await axios.delete(`${API_URL}/api/bookmarks/${existing.id}`)

      setSavedArticles(previous =>
        previous.filter(item => item.id !== existing.id)
      )

      setBookmarks(previous =>
        previous.filter(url => url !== article.url)
      )
    } else {
      if (!article.url) {
        setBookmarkError('This article has no URL and cannot be saved.')
        return
      }

      const response = await axios.post(`${API_URL}/api/bookmarks`, {
        article_url: article.url,
        title: article.title,
        source: article.source,
        category: article.category,
        description: article.description
      })

      const saved = await axios.get(`${API_URL}/api/bookmarks`)

      setSavedArticles(saved.data || [])
      setBookmarks((saved.data || []).map(item => item.article_url))
    }
  } catch (error) {
    setBookmarkError(
      error.response?.data?.detail ||
      'Could not update the bookmark. Please try again.'
    )
  }
}

  const openArticle = article => {
    setSelectedArticle(article)
    setShowSummary(false)
  }

  const resetFilters = () => {
    setQuery('')
    setActiveCategory('All News')
    setSavedOnly(false)
  }

  const refreshNews = async () => {
    setLoading(true)
    setApiError('')

    try {
      const response = await axios.get(`${API_URL}/api/news`, {
        timeout: 20000,
      })

      setArticles((response.data.articles || []).map(normalizeArticle))
    } catch (error) {
      setApiError(
        error.response
          ? `News API returned status ${error.response.status}.`
          : 'Could not connect to NewsIQ. Check that the backend is running.'
      )
    } finally {
      setLoading(false)
    }
  }

  
const generateSummary = async () => {
  if (!selectedArticle) return

  setSummaryLoading(true)
  setSummaryError('')
  setShowSummary(false)

  try {
    const response = await axios.post(`${API_URL}/api/summarize`, {
  title: selectedArticle.title,
  source: selectedArticle.source,
  text: selectedArticle.description,
})
    if (response.data.error) {
      throw new Error(response.data.error)
    }

    setSelectedArticle(previous => ({
      ...previous,
      summary: response.data.summary,
      keyTakeaways: response.data.key_takeaways,
      summaryMethod: response.data.method,
    }))

    setShowSummary(true)
  } catch (error) {
    setSummaryError(
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.message ||
      'Could not generate the summary.'
    )
  } finally {
    setSummaryLoading(false)
  }
}


  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-icon"><Newspaper size={23} /></div>
          <div>
            <strong>NewsIQ</strong>
            <span>YOUR DAILY INTELLIGENCE</span>
          </div>
        </div>

        <div className="side-label">WORKSPACE</div>

        <button
          className={`nav-item ${!savedOnly ? 'nav-active' : ''}`}
          onClick={() => {
            setSavedOnly(false)
            setMobileMenu(false)
          }}
        >
          <Home size={18} /> Discover
        </button>

        <button
          className={`nav-item ${savedOnly ? 'nav-active' : ''}`}
          onClick={() => {
            setSavedOnly(true)
            setMobileMenu(false)
          }}
        >
          <Bookmark size={18} /> Saved articles
          <span className="nav-count">{bookmarks.length}</span>
        </button>

        <div className="side-label category-label">EXPLORE TOPICS</div>

        {categories.map(category => (
          <button
            key={category}
            className={`nav-item ${activeCategory === category ? 'nav-active' : ''}`}
            onClick={() => {
              setActiveCategory(category)
              setSavedOnly(false)
              setMobileMenu(false)
            }}
          >
            <span className="category-dot" />
            {category}
          </button>
        ))}

        <div className="sidebar-bottom">
          <div className="ai-mini">
            <Sparkles size={18} />
            <strong>Intelligence, simplified.</strong>
            <p>Less noise. More knowledge.</p>
          </div>

          <div className="profile">
            <div className="avatar">S</div>
            <div>
              <strong>NewsIQ Reader</strong>
              <span>Personal workspace</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button
            className="icon-button mobile-toggle"
            onClick={() => setMobileMenu(!mobileMenu)}
            aria-label="Toggle menu"
          >
            <Menu size={21} />
          </button>

          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <strong>{savedOnly ? 'Saved articles' : activeCategory}</strong>
          </div>

          <div className="top-actions">
            <span className="live-dot" />
            <span className="live-label">YOUR NEWS SPACE</span>
            <div className="avatar small">S</div>
          </div>
        </header>

        <div className="content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow">
                <Sparkles size={15} /> YOUR WORLD, IN CONTEXT
              </div>
              <h1>
                Stay curious.<br />
                <span>Stay informed.</span>
              </h1>
              <p className="welcome-text">
                A smarter way to explore the stories shaping your world.
              </p>
            </div>

            <div className="hero-art">
              <div className="hero-orbit orbit-one" />
              <div className="hero-orbit orbit-two" />
              <div className="hero-core"><Globe2 size={49} /></div>
              <div className="floating-chip chip-one">
                <Zap size={15} /> AI insights
              </div>
              <div className="floating-chip chip-two">
                <Activity size={15} /> Connected stories
              </div>
            </div>
          </section>

          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon purple"><Newspaper size={19} /></div>
              <span>Articles fetched</span>
              <strong>{articles.length.toString().padStart(2, '0')}</strong>
              <small>From RSS news feeds</small>
            </div>

            <div className="stat-card">
              <div className="stat-icon green"><TrendingUp size={19} /></div>
              <span>Topics to explore</span>
              <strong>{new Set(articles.map(a => a.category)).size}</strong>
              <small>Available news categories</small>
            </div>

            <div className="stat-card">
              <div className="stat-icon orange"><Bookmark size={19} /></div>
              <span>Your reading list</span>
              <strong>{bookmarks.length.toString().padStart(2, '0')}</strong>
              <small>Saved in PostgreSql</small>
            </div>

            <div className="stat-card">
              <div className="stat-icon blue"><Cpu size={19} /></div>
              <span>AI tools</span>
              <strong>03</strong>
              <small>Planned intelligence features</small>
            </div>
          </section>

          <section className="news-section">
            <div className="section-heading">
              <div>
                <div className="eyebrow">THE LATEST</div>
                <h2>
                  {savedOnly
                    ? 'Your reading list'
                    : activeCategory === 'All News'
                      ? 'Discover stories'
                      : activeCategory}
                </h2>
                <p>Explore ideas, developments and perspectives.</p>
              </div>

              <button className="refresh-button" onClick={refreshNews}>
                <RefreshCw size={15} /> Refresh news
              </button>
            </div>

            <div className="filter-row">
              <div className="search-box">
                <Search size={18} />
                <input
                  value={query}
                  onChange={event => setQuery(event.target.value)}
                  placeholder="Search stories, topics or sources..."
                />
                <kbd>/</kbd>
              </div>
              <span className="result-count">{filtered.length} stories</span>
            </div>

            <div className="chips">
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => {
                    setActiveCategory(category)
                    setSavedOnly(false)
                  }}
                  className={`chip ${activeCategory === category ? 'chip-active' : ''}`}
                >
                  {category}
                </button>
              ))}
            </div>

            {savedOnly && bookmarkLoading ? (
  <div className="empty-state">
    <RefreshCw size={28} />
    <h3>Loading saved articles...</h3>
    <p>Fetching your reading list from the database.</p>
  </div>
) : savedOnly && bookmarkError ? (
  <div className="empty-state">
    <Activity size={28} />
    <h3>Unable to load saved articles</h3>
    <p>{bookmarkError}</p>
  </div>
) : loading && !savedOnly ? (
  <div className="empty-state">
    <RefreshCw size={28} />
    <h3>Discovering the latest stories...</h3>
    <p>NewsIQ is fetching articles from its news feeds.</p>
  </div>
) : apiError && !savedOnly ? (
  <div className="empty-state">
    <Activity size={28} />
    <h3>Unable to load news</h3>
    <p>{apiError}</p>
    <button className="read-button" onClick={refreshNews}>
      Try again <ChevronRight size={15} />
    </button>
  </div>
) : filtered.length ? (
              <div className="article-grid">
                {filtered.map((article, index) => (
                  <article
                    className={`article-card ${index === 0 ? 'featured-card' : ''}`}
                    key={article.id}
                  >
                    <button
                      className="article-image"
                      style={{
                        backgroundColor: article.color || '#e8e7ff',
                        backgroundImage: article.image
                          ? `url("${article.image}")`
                          : 'linear-gradient(135deg, #e8e7ff, #f3f4fa)',
                      }}
                      onClick={() => openArticle(article)}
                      aria-label={`Read ${article.title}`}
                    >
                      <span className="article-tag">{article.tag}</span>
                      <span className="image-arrow"><ArrowUpRight size={17} /></span>
                    </button>

                    <div className="article-body">
                      <div className="article-meta">
                        <span>{article.source}</span>
                        <span>
                          <Clock3 size={12} />
                          {article.time || 'Recently published'}
                        </span>
                      </div>

                      <h3>
                        <button
                          className="title-button"
                          onClick={() => openArticle(article)}
                        >
                          {article.title}
                        </button>
                      </h3>

                      <p>{article.description}</p>

                      <div className="article-footer">
                        <button
                          className="read-button"
                          onClick={() => openArticle(article)}
                        >
                          Explore story <ChevronRight size={15} />
                        </button>

                        <button
                          className={`bookmark-button ${bookmarks.includes(article.url) ? 'is-bookmarked' : ''}`}
                          onClick={() => toggleBookmark(article)}
                          aria-label="Toggle bookmark"
                        >
                          <Bookmark
                            size={18}
                            fill={bookmarks.includes(article.url) ? 'currentColor' : 'none'}
                          />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Search size={28} />
                <h3>No stories found</h3>
                <p>
                  Try another search or explore a different category.
                </p>
                <button className="read-button" onClick={resetFilters}>
                  Show all stories <ChevronRight size={15} />
                </button>
              </div>
            )}

            <div className="demo-notice">
              <Sparkles size={16} />
              <span>
                <strong>Live RSS mode:</strong> Headlines and descriptions
                are fetched from news feeds. AI-generated summaries and
                persistent storage will be added in upcoming phases.
              </span>
            </div>
          </section>

          <footer className="footer">
            <span>NewsIQ © 2026</span>
            <span>Built for a smarter news experience</span>
            <span><span className="live-dot" /> RSS connected</span>
          </footer>
        </div>
      </main>

      {selectedArticle && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedArticle(null)}
        >
          <section
            className="article-modal"
            onClick={event => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setSelectedArticle(null)}
              aria-label="Close article"
            >
              ×
            </button>

            <span className="article-tag modal-tag">{selectedArticle.tag}</span>

            <div className="eyebrow modal-source">
              {selectedArticle.source} · {selectedArticle.time || 'Recently published'}
            </div>

            <h2>{selectedArticle.title}</h2>
            <p className="modal-description">{selectedArticle.description}</p>

            
<div className="summary-panel">
  <div className="summary-title">
    <Sparkles size={18} />
    NewsIQ AI Summary
    <span>NLP</span>
  </div>

  <p>{selectedArticle.summary}</p>

  {selectedArticle.summaryMethod && (
    <small>Method: {selectedArticle.summaryMethod}</small>
  )}
</div>

<div className="modal-actions">
  <button
    className="read-button"
    onClick={() => toggleBookmark(selectedArticle.id)}
  >
    <Bookmark size={16} />
    {bookmarks.includes(selectedArticle.id)
      ? 'Remove bookmark'
      : 'Save article'}
  </button>

  <button
    className="refresh-button"
    onClick={generateSummary}
    disabled={summaryLoading}
  >
    <Sparkles size={15} />
    {summaryLoading ? 'Summarizing...' : 'Generate AI summary'}
  </button>

  {selectedArticle.url && (
    <button
      className="refresh-button"
      onClick={() => window.open(
        selectedArticle.url,
        '_blank',
        'noopener,noreferrer'
      )}
    >
      Read original article <ArrowUpRight size={15} />
    </button>
  )}
</div>

{summaryError && (
  <p role="alert" className="summary-error">
    {summaryError}
  </p>
)}

{showSummary && selectedArticle.keyTakeaways?.length > 0 && (
  <div className="takeaways">
    <strong>Key takeaways</strong>
    <ul>
      {selectedArticle.keyTakeaways.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  </div>
)}


            <div className="modal-actions">
              <button
                className="read-button"
                onClick={() => toggleBookmark(selectedArticle.id)}
              >
                <Bookmark size={16} />
                {bookmarks.includes(selectedArticle.id)
                  ? 'Remove bookmark'
                  : 'Save article'}
              </button>

              <button
                className="refresh-button"
                onClick={() => setShowSummary(!showSummary)}
              >
                {showSummary ? 'Hide key takeaways' : 'Show key takeaways'}
              </button>

              {selectedArticle.url && (
                <button
                  className="refresh-button"
                  onClick={() => window.open(
                    selectedArticle.url,
                    '_blank',
                    'noopener,noreferrer'
                  )}
                >
                  Read original article <ArrowUpRight size={15} />
                </button>
              )}
            </div>

            {showSummary && (
              <ul className="takeaways">
                <li>Read the original article for complete context.</li>
                <li>Compare reporting from multiple independent sources.</li>
                <li>Check publication dates and supporting evidence.</li>
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

export default App
