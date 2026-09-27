import Catalog from '../Catalog';
import { catalog } from '../../lib/catalog';

export const dynamic = 'force-static';
export default function Page() { return <Catalog initialCatalog={catalog} />; }
