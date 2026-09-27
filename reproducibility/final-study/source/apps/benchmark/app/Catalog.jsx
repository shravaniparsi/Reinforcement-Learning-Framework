'use client';

import { useEffect, useState } from 'react';

export default function Catalog({ initialCatalog = null, catalogUrl = '/api/catalog' }) {
  const [data, setData] = useState(initialCatalog);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);
  const [cart, setCart] = useState([]);
  useEffect(() => {
    if (initialCatalog) return;
    const controller = new AbortController();
    fetch(catalogUrl, { signal: controller.signal, cache: 'no-store' })
      .then(response => {
        if (!response.ok) throw new Error(`Catalog HTTP ${response.status}`);
        return response.json();
      }).then(setData).catch(error => {
        if (error.name !== 'AbortError') setError(error.message);
      });
    return () => controller.abort();
  }, [initialCatalog, catalogUrl]);
  useEffect(() => {
    if (!data) return;
    performance.mark('catalog-interactive');
    setReady(true);
  }, [data]);
  return <main data-ready={ready ? 'true' : 'false'} data-version={data?.version || ''}>
    <header><p>WORKSPACE COLLECTION</p><h1>Build a calmer workspace</h1>
      <p>Browse the collection and add an item to your cart.</p></header>
    <div id="cart" aria-live="polite">
      <span>Items: <output id="cart-count">{cart.length}</output></span>
      <span>Total: $<output id="cart-total">{(cart.reduce((sum, price) => sum + price, 0) / 100).toFixed(2)}</output></span>
    </div>
    {error && <p role="alert">{error}</p>}
    {!data && <p>Loading collection…</p>}
    <section className="catalog" aria-label="Products">
      {data?.products.map(product => <article key={product.id} data-product-id={product.id}>
        <div className="swatch" aria-hidden="true" />
        <h2>{product.name}</h2><p>{product.description}</p>
        <p data-price>{(product.priceCents / 100).toFixed(2)}</p>
        <button onClick={() => setCart(previous => [...previous, product.priceCents])}>Add to cart</button>
      </article>)}
    </section>
  </main>;
}
