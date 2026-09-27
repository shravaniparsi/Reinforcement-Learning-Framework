'use client';
import { useEffect, useState } from 'react';

export default function ArticleFeed({ initialFeed = null, tag, offset, queryMode = 'scan' }) {
  const [data, setData] = useState(initialFeed);
  const [ready, setReady] = useState(false);
  const [saved, setSaved] = useState([]);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (initialFeed) return;
    const controller = new AbortController();
    fetch(`/api/feed?tag=${tag}&offset=${offset}&query_mode=${queryMode}`, { cache: 'no-store', signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error(`Feed HTTP ${response.status}`);
        return response.json();
      }).then(setData).catch(error => {
        if (error.name !== 'AbortError') setError(error.message);
      });
    return () => controller.abort();
  }, [initialFeed, tag, offset, queryMode]);
  useEffect(() => {
    if (data) { performance.mark('feed-interactive'); setReady(true); }
  }, [data]);
  return <main data-ready={ready ? 'true' : 'false'} data-backend={data ? JSON.stringify(data.backend) : ''}>
    <header><p>ENGINEERING NOTEBOOK</p><h1>Ideas worth reading</h1>
      <p>Notes on {tag}. Save an article to your reading list.</p></header>
    <p>Articles: <output id="article-count">{data?.articlesCount ?? '…'}</output> · Saved: <output id="saved-count">{saved.length}</output></p>
    {error && <p role="alert">{error}</p>}
    {!data && <p>Loading articles…</p>}
    <section aria-label="Articles" style={{ display: 'grid', gap: 16 }}>
      {data?.articles.map(article => <article key={article.slug} data-slug={article.slug}>
        <h2>{article.title}</h2><p data-description>{article.description}</p>
        <p data-tag>{article.tagList.join(', ')}</p>
        <button aria-pressed={saved.includes(article.slug)} onClick={() => setSaved(previous =>
          previous.includes(article.slug) ? previous.filter(slug => slug !== article.slug) : [...previous, article.slug])}>
          {saved.includes(article.slug) ? 'Remove from reading list' : 'Save article'}
        </button>
      </article>)}
    </section>
  </main>;
}
