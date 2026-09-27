import './style.css';

export const metadata = { title: 'Rendering benchmark catalog', description: 'Local measurement fixture' };

export default function Layout({ children }) {
  return <html lang="en"><body>{children}</body></html>;
}
