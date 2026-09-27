import Catalog from '../Catalog';
import { catalog } from '../../lib/catalog';

export const dynamic = 'force-dynamic';
export default function Page() { return <Catalog initialCatalog={catalog} />; }
