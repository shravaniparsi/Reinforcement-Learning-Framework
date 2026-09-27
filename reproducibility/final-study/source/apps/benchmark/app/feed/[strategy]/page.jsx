import { notFound } from 'next/navigation';
import ArticleFeed from '../../ArticleFeed';
import { articleFeed, validFeed } from '../../../lib/feed';
export const dynamic = 'force-dynamic';
export default async function Page({ params, searchParams }) {
  const { strategy } = await params;
  const { tag = 'rendering', offset = '0', query_mode = 'scan' } = await searchParams;
  if (!['csr', 'ssr'].includes(strategy) || !validFeed(tag, offset, query_mode)) notFound();
  return <ArticleFeed initialFeed={strategy === 'ssr' ? await articleFeed(tag, offset, query_mode) : null} tag={tag} offset={offset} queryMode={query_mode} />;
}
