'use client';

import { createContext, useContext } from 'react';
import type { APIClient } from './types';
import { localAPIClient } from './local';

const APIContext = createContext<APIClient>(localAPIClient);

interface APIProviderProps {
  client?: APIClient;
  children: React.ReactNode;
}

export function APIProvider({ client, children }: APIProviderProps) {
  return (
    <APIContext.Provider value={client ?? localAPIClient}>
      {children}
    </APIContext.Provider>
  );
}

export function useAPI(): APIClient {
  return useContext(APIContext);
}
