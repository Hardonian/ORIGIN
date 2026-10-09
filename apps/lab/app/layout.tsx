import "./globals.css";
import type { Metadata } from "next";
import Nav from "./nav";
import ToastContainer from "./ToastContainer";

export const metadata: Metadata = {
  title: "ORIGIN Research Lab",
  description: "Open Research Into General Intelligence — research-lab interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="top">
          <span className="brand">ORIGIN</span>
          <Nav />
        </header>
        <main>{children}</main>
        <ToastContainer />
      </body>
    </html>
  );
}
