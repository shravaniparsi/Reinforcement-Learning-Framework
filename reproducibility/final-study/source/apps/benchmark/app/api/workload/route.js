import { cookies } from 'next/headers';
import { workloadCatalog } from '../../../lib/workloads';

export const dynamic = 'force-dynamic';
export async function GET(request) {
  const params = new URL(request.url).searchParams;
  const revision = params.get('revision') || '0';
  const identity = (await cookies()).get('fixture-user')?.value || 'guest';
  try {
    if (!/^\d+$/.test(revision)) throw new Error('Invalid revision');
    return Response.json(workloadCatalog(params.get('workload'), Number(revision), identity), {
      headers: { 'Cache-Control': 'private, no-store', 'Vary': 'Cookie' },
    });
  } catch {
    return Response.json({ error: 'Invalid fixture request' }, { status: 400 });
  }
}
