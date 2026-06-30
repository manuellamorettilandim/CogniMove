import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CogniMove",
  description: "Dashboard de mobilidade inteligente com IA"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="bg-canvas font-sans text-slate-950 antialiased">
        {children}
      </body>
    </html>
  );
}
