import Link from "next/link";
import { Footer, Topbar } from "@/components/Chrome";

export default function NotFound() {
  return (
    <main>
      <Topbar />
      <section className="error-page">
        <div className="error-code">404 / INVALID SPECIMEN</div>
        <h1>WALLET NOT FOUND.</h1>
        <p>Either the address is wrong or the wallet successfully escaped the autopsy.</p>
        <div>
          <Link className="button-link" href="/">
            BACK TO THE LAB
          </Link>
        </div>
      </section>
      <Footer />
    </main>
  );
}
