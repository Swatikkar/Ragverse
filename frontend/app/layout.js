import "./globals.css";

export const metadata = {
  title: "Ragverse",
  description: "Multimodal AI Research Assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white antialiased">
        {children}
      </body>
    </html>
  );
}