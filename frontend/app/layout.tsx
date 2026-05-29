import "./globals.css";
import GlobalControls from "./components/GlobalControls";

export const metadata = {
  title: "NDSP Trading Bot",
  description: "NDSP Binance Trading Bot Dashboard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body><GlobalControls />
        {children}</body>
    </html>
  );
}
