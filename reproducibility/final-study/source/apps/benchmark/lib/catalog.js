// Immutable, local fixture: identical content for every strategy.
// SSG is feasible here because this pilot makes no live-freshness requirement.
export const catalog = {
  version: 'catalog-v1',
  products: Array.from({ length: 24 }, (_, index) => ({
    id: `product-${index + 1}`,
    name: `Desk accessory ${String(index + 1).padStart(2, '0')}`,
    description: 'A compact everyday accessory for a comfortable, organized workspace.',
    priceCents: 1200 + index * 175,
  })),
};
