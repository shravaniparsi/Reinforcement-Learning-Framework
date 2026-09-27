export const liveModes = ['bypass', 'cached', 'refresh'];
export async function liveCatalog(mode) {
  if (!liveModes.includes(mode)) throw new Error('Invalid cache mode');
  const response = await fetch(`http://127.0.0.1:3202/catalog?mode=${mode}`, {
    cache: 'no-store', signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error(`Backend HTTP ${response.status}`);
  return response.json();
}
