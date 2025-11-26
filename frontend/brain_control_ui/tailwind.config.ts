import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/components/**/*.{ts,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brain: {
          bg: "#05070A",
          panel: "#0B0F14",
          panelSoft: "#11161F",
          gold: "#D6B46A",
          goldStrong: "#E9C98C",
          blue: "#3BA0F2",
          purple: "#A060FF",
          green: "#4ED6A0",
          red: "#FF4C4C"
        }
      },
      boxShadow: {
        "brain-glow": "0 0 50px -20px rgba(233,201,140,0.4)"
      },
      borderRadius: {
        "2xl": "1.25rem"
      }
    }
  },
  plugins: [],
}

export default config
