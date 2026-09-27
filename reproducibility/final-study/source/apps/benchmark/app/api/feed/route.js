import { articleFeed, validFeed } from '../../../lib/feed';
export const dynamic = 'force-dynamic';
export async function GET(request) {
  const params = new URL(request.url).searchParams;
  const tag = params.get('tag') || 'rendering';
  const offset = params.get('offset') || '0';
  const queryMode = params.get('query_mode') || 'scan';
  if (!validFeed(tag, offset, queryMode)) return Response.json({ error: 'Invalid query' }, { status: 400 });
  return Response.json(await articleFeed(tag, offset, queryMode), { headers: { 'Cache-Control': 'no-store' } });
}
