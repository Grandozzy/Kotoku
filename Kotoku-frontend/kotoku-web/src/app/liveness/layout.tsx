export const metadata = { title: "Face check | Kotoku" };

export default function LivenessLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0, background: "#000" }}>{children}</body>
    </html>
  );
}
