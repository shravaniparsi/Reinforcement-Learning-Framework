export default function Page() {
  return <main><h1>Rendering measurement pilot</h1>
    <p>Three implementations of the same local catalog and cart interaction.</p>
    <ul>{['csr', 'ssr', 'ssg'].map(strategy => <li key={strategy}>
      <a href={`/${strategy}`}>{strategy.toUpperCase()}</a></li>)}</ul>
    <p>Use the production build and experiment runner for measurements.</p>
  </main>;
}
