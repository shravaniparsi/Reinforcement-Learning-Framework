/* Explicit fixture adaptation: fully consume same-origin Svelte data responses.
 * Does not handle deferred streams or suppress fetch/body errors. */
(() => {
  const installed = Symbol.for('rl-rendering.buffered-data.v1');
  if (globalThis[installed]) return;
  const originalFetch = globalThis.fetch;
  const decorate = (response, metadata) => {
    for (const name of ['url', 'redirected', 'type']) {
      Object.defineProperty(response, name, { value: metadata[name] });
    }
    // Network response headers are immutable; keep that behavior after wrapping.
    for (const name of ['append', 'delete', 'set']) {
      Object.defineProperty(response.headers, name, { value() { throw new TypeError('Immutable response headers'); } });
    }
    const clone = response.clone;
    Object.defineProperty(response, 'clone', { value() { return decorate(clone.call(this), metadata); } });
    return response;
  };
  globalThis.fetch = async function (...args) {
    const response = await originalFetch.apply(this, args);
    const method = String(args[1]?.method ?? (args[0] instanceof Request ? args[0].method : 'GET')).toUpperCase();
    if (method !== 'GET' || response.status !== 200 || !response.url) return response;
    const url = new URL(response.url);
    if (url.origin !== location.origin || url.pathname !== '/__data.json' ||
        response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') return response;
    // Byte buffering preserves payload encoding and propagates body-read failures.
    const bytes = await response.arrayBuffer();
    return decorate(new Response(bytes, {
      status: response.status, statusText: response.statusText, headers: response.headers
    }), response);
  };
  Object.defineProperty(globalThis, installed, { value: true });
})();
