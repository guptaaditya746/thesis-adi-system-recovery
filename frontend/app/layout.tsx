import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ADI Research Workbench',
  description: 'Inspectable ontology-guided scientific KG pipeline',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
