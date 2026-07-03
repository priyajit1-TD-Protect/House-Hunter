import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GTA House Hunter",
  description: "Smart Toronto home search for Sachi — scored by income, schools, and transit",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#F5F5F5] font-body antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
