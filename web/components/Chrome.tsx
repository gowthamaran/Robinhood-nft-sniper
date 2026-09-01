import Link from "next/link";

export function Topbar() {
  return (
    <header className="topbar">
      <Link className="brand" href="/">
        FUMBLED<span className="brand-dot">.</span>LOL
      </Link>
      <nav className="nav" aria-label="Main navigation">
        <Link href="/methodology">METHODOLOGY</Link>
        <Link href="/battle">WALLET BATTLE</Link>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <Link className="brand" href="/">
        FUMBLED<span className="brand-dot">.</span>LOL
      </Link>
      <p>
        Public blockchain analysis. Fumbled is hypothetical missed upside, not money lost. Data can be
        incomplete; DYOR.
      </p>
      <p className="credit">
        built by{" "}
        <a href="https://x.com/themaran" target="_blank" rel="noopener noreferrer">
          Themaran ↗
        </a>
      </p>
    </footer>
  );
}
