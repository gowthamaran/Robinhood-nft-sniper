"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { isAddress } from "@/lib/format";

export function WalletSearch({ autoFocus = false }: { autoFocus?: boolean }) {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const address = value.trim();
    if (!isAddress(address)) {
      setError("THAT IS NOT AN ETHEREUM ADDRESS. IT LOOKS LIKE 0x FOLLOWED BY 40 CHARACTERS.");
      return;
    }
    setError(null);
    setPending(true);
    router.push(`/wallet/${address.toLowerCase()}`);
  }

  return (
    <>
      <form className="wallet-form" onSubmit={onSubmit} noValidate>
        <label className="sr-only" htmlFor="wallet">
          Ethereum wallet address
        </label>
        <input
          id="wallet"
          className="wallet-input"
          placeholder="0x..."
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          autoFocus={autoFocus}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <button className="wallet-button" type="submit" disabled={pending}>
          {pending ? "READING..." : "AUTOPSY MY WALLET →"}
        </button>
      </form>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}
