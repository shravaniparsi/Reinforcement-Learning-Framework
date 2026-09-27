import { liveCatalog, liveModes } from '../../../lib/live';
export const dynamic = 'force-dynamic';
export async function GET(request) {
  const mode = new URL(request.url).searchParams.get('mode');
  if (!liveModes.includes(mode)) return Response.json({ error: 'Invalid mode' }, { status: 400 });
  return Response.json(await liveCatalog(mode), { headers: { 'Cache-Control': 'no-store' } });
}
