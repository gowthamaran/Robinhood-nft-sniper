type Mood = "laughing" | "neutral";

export function Mascot({ mood = "neutral", className = "" }: { mood?: Mood; className?: string }) {
  return (
    <svg
      className={`mascot ${mood === "laughing" ? "laughing" : ""} ${className}`.trim()}
      viewBox="0 0 520 520"
      role="img"
      aria-label="The Fumbled.lol mascot judging this wallet"
    >
      <title>The Fumbled.lol mascot judging this wallet</title>
      <path
        d="M116 176C133 77 214 39 304 64c94 27 136 111 102 199 42 70 14 159-72 186-105 34-218-17-242-118-13-54 0-108 24-155Z"
        fill="#F1EADB"
        stroke="#13130F"
        strokeWidth="12"
      />
      <path
        d="M151 122 117 62l78 38M343 91l48-52 16 85"
        fill="#E3432F"
        stroke="#13130F"
        strokeWidth="12"
        strokeLinejoin="round"
      />
      <path d="M150 184c50-32 174-34 229 0" fill="none" stroke="#13130F" strokeWidth="18" strokeLinecap="round" />
      <g transform="rotate(-4 265 190)">
        <rect x="143" y="151" width="105" height="67" rx="8" fill="#13130F" />
        <rect x="278" y="151" width="105" height="67" rx="8" fill="#13130F" />
        <path d="M248 177h30" stroke="#13130F" strokeWidth="12" />
        <path d="m156 163 36 43M291 163l36 43" stroke="#F1EADB" strokeWidth="7" opacity=".35" />
      </g>
      {mood === "laughing" ? (
        <>
          <path
            d="M176 281c44 92 139 91 184 0-62 31-122 31-184 0Z"
            fill="#E3432F"
            stroke="#13130F"
            strokeWidth="12"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M205 301c37-11 79-10 118 0" stroke="#F1EADB" strokeWidth="10" />
        </>
      ) : (
        <path
          d="M190 300c49 20 96 19 141-2"
          fill="none"
          stroke="#13130F"
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      <path d="M174 372c56 36 126 36 178 0" fill="none" stroke="#C8A13A" strokeWidth="13" strokeLinecap="round" />
      <circle cx="225" cy="393" r="21" fill="#F5D90A" stroke="#13130F" strokeWidth="8" />
      <path d="M225 383v20M215 393h20" stroke="#13130F" strokeWidth="5" />
      <g className="tear" fill="#75C9F2" stroke="#13130F" strokeWidth="4">
        <path d="M171 220c-18 29-20 41-4 44 17 3 19-14 4-44Z" />
        <path d="M359 220c18 29 20 41 4 44-17 3-19-14-4-44Z" />
      </g>
    </svg>
  );
}
