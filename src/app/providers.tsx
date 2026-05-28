'use client';

import { APIProvider } from '@/lib/api';

export function Providers({ children }: { children: React.ReactNode }) {
  return <APIProvider>{children}</APIProvider>;
}
