import "./globals.css";

export const metadata = {
  title: "TV Fiscal WebMonitor",
  description: "Plataforma de monitoramento editorial e publicitario digital",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-br">
      <body
        style={{
          margin: 0,
          fontFamily: "Arial, sans-serif",
          background: "#f4f6fa",
          color: "#222",
        }}
      >
        {children}
      </body>
    </html>
  );
}