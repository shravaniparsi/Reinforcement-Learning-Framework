import { notFound } from 'next/navigation';
import Catalog from '../../Catalog';
import { liveCatalog, liveModes } from '../../../lib/live';
export const dynamic = 'force-dynamic';
export default async function Page({ params, searchParams }) {
  const { strategy } = await params;
  const { mode = 'bypass' } = await searchParams;
  if (!['csr', 'ssr'].includes(strategy) || !liveModes.includes(mode)) notFound();
  return <Catalog initialCatalog={strategy === 'ssr' ? await liveCatalog(mode) : null}
    catalogUrl={`/api/live?mode=${mode}`} />;
}
