import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import { BriefGenerationProvider } from "./context/BriefGenerationContext";
import { ModeProvider } from "./context/ModeContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const sourceSerif = Source_Serif_4({ subsets: ["latin"], variable: "--font-serif" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "ChiefOS - AI Personal Chief of Staff",
  description: "What should I focus on today?",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-cream-100 font-sans text-ink antialiased">
        <ModeProvider>
          <BriefGenerationProvider>{children}</BriefGenerationProvider>
        </ModeProvider>
      </body>
    </html>
  );
}
