import type { Metadata } from "next";
import "./globals.css";
import { GuardianSessionProvider } from "@/providers/guardian-session-provider";

export const metadata: Metadata = {
  title: "Guardian Nexus | Digital Protection System",
  description:
    "Real-time AI digital guardian — protecting seniors and vulnerable users from scam calls, phishing, impersonation, and social engineering attacks.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body 
        className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)] font-[var(--font-sans)]"
        suppressHydrationWarning
      >
        <GuardianSessionProvider>{children}</GuardianSessionProvider>
      </body>
    </html>
  );
}
