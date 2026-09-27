export const feedTags = ['rendering', 'accessibility'];
export function validFeed(tag, offset, queryMode = 'scan') {
  return ['scan', 'indexed'].includes(queryMode) && feedTags.includes(tag) && /^\d+$/.test(String(offset)) && Number(offset) <= 100;
}
export async function articleFeed(tag = 'rendering', offset = '0', queryMode = 'scan') {
  if (!validFeed(tag, offset, queryMode)) throw new Error('Invalid feed query');
  const response = await fetch(`http://127.0.0.1:3203/articles?tag=${tag}&offset=${offset}&query_mode=${queryMode}`, {
    cache: 'no-store', signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error(`Article backend HTTP ${response.status}`);
  return response.json();
}
