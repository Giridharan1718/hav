import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/components/AuthProvider";

export const metadata: Metadata = {
  title: {
    default: "HVA Assist — Government schemes in your language",
    template: "%s · HVA Assist",
  },
  description:
    "Independent, privacy-first assistance to find Indian government schemes, check documented criteria and prepare application drafts in English, Hindi or Tamil.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await cookies();
  const cookieLanguage = store.get("hva_lang")?.value;
  const lang = cookieLanguage === "hi" || cookieLanguage === "ta" ? cookieLanguage : "en";
  return (
    <html lang={lang}>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
