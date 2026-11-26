import type { Config } from "tailwindcss";

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: v("bg"), panel: v("panel"), panel2: v("panel2"), line: v("line"),
        fg: v("fg"), muted: v("muted"), accent: v("accent"),
        pos: v("pos"), neg: v("neg"), warn: v("warn"),
      },
      fontFamily: { mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"] },
    },
  },
  plugins: [],
} satisfies Config;
