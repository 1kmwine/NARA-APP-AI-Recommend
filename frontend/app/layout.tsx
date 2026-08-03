import "../styles/design-system.css";
import "./globals.css";

export const metadata = { title: "AI 와인 추천" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
