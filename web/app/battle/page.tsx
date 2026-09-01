import type { Metadata } from "next";
import { Footer, Topbar } from "@/components/Chrome";
import { BattleClient } from "@/components/BattleClient";

export const metadata: Metadata = {
  title: "Wallet Battle",
  description: "Put two wallets side by side and find out which one actually knows what it is doing.",
};

export default function BattlePage() {
  return (
    <main>
      <Topbar />
      <section className="battle-hero">
        <div className="kicker">HEAD TO HEAD / PUBLIC DATA</div>
        <h1>
          WHOSE WALLET IS <span className="slash">WORSE?</span>
        </h1>
        <p className="subhead">
          Two addresses. Same maths. One of you has to read the result out loud.
        </p>
        <BattleClient />
      </section>
      <Footer />
    </main>
  );
}
