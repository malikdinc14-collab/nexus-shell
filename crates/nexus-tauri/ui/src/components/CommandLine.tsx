// CommandLine — vim ex-mode style : prompt.
// Ctrl+\ to open. Parses commands like :q, :wq, :set gap 12.

import { useEffect, useRef, useState } from "react";

interface Props {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  onExecute: (raw: string) => void;
}

export default function CommandLine({ isOpen, setIsOpen, onExecute }: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setValue("");
      // Small delay so the element mounts before focus
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = value.trim();
      if (trimmed) {
        onExecute(trimmed);
      }
      setIsOpen(false);
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
    }
  };

  return (
    <div
      style={{
        height: 28,
        display: "flex",
        alignItems: "center",
        padding: "0 10px",
        background: "var(--bg-dark)",
        borderTop: "1px solid var(--border)",
        flexShrink: 0,
        gap: 6,
      }}
    >
      <span
        style={{
          color: "var(--accent)",
          fontSize: 13,
          fontWeight: "bold",
          userSelect: "none",
        }}
      >
        :
      </span>
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="command..."
        style={{
          flex: 1,
          background: "transparent",
          border: "none",
          outline: "none",
          color: "var(--text-bright)",
          fontFamily: "inherit",
          fontSize: 13,
          caretColor: "var(--accent)",
        }}
      />
      <span
        style={{
          fontSize: 10,
          color: "var(--text-dim)",
          userSelect: "none",
        }}
      >
        Enter to run · Esc to cancel
      </span>
    </div>
  );
}
