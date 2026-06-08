import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI SDR Agent",
  description: "Autonomous outbound sales pipeline",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen font-sans">
        <nav className="border-b border-gray-800 px-6 py-4 flex items-center gap-8">
          <span className="font-bold text-white text-lg tracking-tight">AI SDR Agent</span>
          <a href="/" className="text-sm text-gray-400 hover:text-white transition-colors">Dashboard</a>
          <a href="/campaigns" className="text-sm text-gray-400 hover:text-white transition-colors">Campaigns</a>
          <a href="/prospects" className="text-sm text-gray-400 hover:text-white transition-colors">Prospects</a>
          <a href="/replies" className="text-sm text-gray-400 hover:text-white transition-colors">Replies</a>
        </nav>
        <main className="px-6 py-8 max-w-6xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
