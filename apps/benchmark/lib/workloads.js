import { catalog } from './catalog';

export const workloads = ['updates', 'personalized'];
export const strategies = ['csr', 'ssr'];

export function workloadCatalog(workload, revision, identity = 'guest') {
  if (!workloads.includes(workload) || !Number.isInteger(revision) || revision < 0 || revision > 1000) {
    throw new Error('Invalid workload or revision');
  }
  if (!['guest', 'alice', 'bob'].includes(identity)) throw new Error('Invalid fixture identity');
  const owner = workload === 'personalized' ? identity : 'public';
  const discount = owner === 'alice' ? 100 : owner === 'bob' ? 200 : 0;
  return {
    version: `${workload}-r${revision}-${owner}`,
    products: catalog.products.map(product => ({
      ...product,
      name: `${product.name} · revision ${revision}${workload === 'personalized' ? ` · ${owner}` : ''}`,
      priceCents: product.priceCents + revision * 25 - discount,
    })),
  };
}
