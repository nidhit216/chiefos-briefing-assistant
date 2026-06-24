import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
