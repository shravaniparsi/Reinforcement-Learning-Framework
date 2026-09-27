import { cookies } from 'next/headers';
import { notFound } from 'next/navigation';
import Catalog from '../../../Catalog';
import { workloadCatalog, workloads, strategies } from '../../../../lib/workloads';

export const dynamic = 'force-dynamic';

export default async function Page({ params, searchParams }) {
  const { workload, strategy } = await params;
  const { revision = '0' } = await searchParams;
  if (!workloads.includes(workload) || !strategies.includes(strategy) || !/^\d+$/.test(revision) || Number(revision) > 1000) notFound();
  const identity = (await cookies()).get('fixture-user')?.value || 'guest';
  if (!['guest', 'alice', 'bob'].includes(identity)) notFound();
  const data = workloadCatalog(workload, Number(revision), identity);
  return <Catalog initialCatalog={strategy === 'ssr' ? data : null}
    catalogUrl={`/api/workload?workload=${workload}&revision=${revision}`} />;
}
