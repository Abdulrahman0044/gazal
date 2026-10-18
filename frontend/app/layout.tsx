import type { Metadata } from 'next';
export const metadata: Metadata = {
  title: { default: 'GAZAL. · Work & growth, connected', template: '%s · GAZAL.' },
  description: 'A shared workspace for teams, projects, remote work and product growth.',
  robots: { index: false, follow: false }
};
export default function RootLayout({ children }: {children: React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
