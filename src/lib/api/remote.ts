import type {
  APIClient,
  AvatarAPI,
  VersionAPI,
  TemplateAPI,
  PipelineAPI,
  SaveAvatarRequest,
  AvatarRecord,
} from './types';
import type { AvatarVersion } from '@/types/editor';
import type { TemplateMetadata } from '@/types/template';

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_PREFIX = `${BASE_URL}/api/v1`;

async function apiFetch<T>(
  url: string,
  options?: RequestInit & { nullOn404?: boolean }
): Promise<T> {
  const { nullOn404, ...fetchOptions } = options ?? {};

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };

  // Placeholder for future auth token
  // const token = getAuthToken();
  // if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...fetchOptions, headers });

  if (res.status === 404 && nullOn404) {
    return null as T;
  }

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(
      `API error ${res.status}: ${res.statusText}${body ? ` - ${body}` : ''}`
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

// --- Avatar API (HTTP) ---

const remoteAvatarAPI: AvatarAPI = {
  async saveAvatar(data: SaveAvatarRequest): Promise<AvatarRecord> {
    return apiFetch<AvatarRecord>(
      `${API_PREFIX}/avatars/${data.avatarId}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          templateId: data.templateId,
          parameters: data.parameters,
        }),
      }
    );
  },

  async loadAvatar(avatarId: string): Promise<AvatarRecord | null> {
    return apiFetch<AvatarRecord | null>(
      `${API_PREFIX}/avatars/${avatarId}`,
      { nullOn404: true }
    );
  },

  async listAvatars(): Promise<AvatarRecord[]> {
    return apiFetch<AvatarRecord[]>(`${API_PREFIX}/avatars`);
  },

  async deleteAvatar(avatarId: string): Promise<void> {
    return apiFetch<void>(
      `${API_PREFIX}/avatars/${avatarId}`,
      { method: 'DELETE' }
    );
  },
};

// --- Version API (HTTP) ---

const remoteVersionAPI: VersionAPI = {
  async saveVersion(
    avatarId: string,
    version: AvatarVersion
  ): Promise<void> {
    return apiFetch<void>(
      `${API_PREFIX}/avatars/${avatarId}/versions`,
      {
        method: 'POST',
        body: JSON.stringify(version),
      }
    );
  },

  async listVersions(avatarId: string): Promise<AvatarVersion[]> {
    return apiFetch<AvatarVersion[]>(
      `${API_PREFIX}/avatars/${avatarId}/versions`
    );
  },

  async deleteVersion(
    avatarId: string,
    versionId: string
  ): Promise<void> {
    return apiFetch<void>(
      `${API_PREFIX}/avatars/${avatarId}/versions/${versionId}`,
      { method: 'DELETE' }
    );
  },

  async updateVersion(
    avatarId: string,
    versionId: string,
    updates: Partial<Pick<AvatarVersion, 'name'>>
  ): Promise<void> {
    return apiFetch<void>(
      `${API_PREFIX}/avatars/${avatarId}/versions/${versionId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(updates),
      }
    );
  },
};

// --- Template API (HTTP) ---

const remoteTemplateAPI: TemplateAPI = {
  async listTemplates(): Promise<TemplateMetadata[]> {
    return apiFetch<TemplateMetadata[]>(`${API_PREFIX}/templates`);
  },

  async getTemplate(
    templateId: string
  ): Promise<TemplateMetadata | null> {
    return apiFetch<TemplateMetadata | null>(
      `${API_PREFIX}/templates/${templateId}`,
      { nullOn404: true }
    );
  },
};

// --- Pipeline API (uses existing Next.js API route) ---

const remotePipelineAPI: PipelineAPI = {
  async extractFeatures(imageFile: File) {
    const formData = new FormData();
    formData.append('image', imageFile);

    const res = await fetch('/api/pipeline/face-keys', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Pipeline error ${res.status}: ${res.statusText}`);
    }

    return res.json();
  },
};

// --- Combined Client ---

export const remoteAPIClient: APIClient = {
  avatar: remoteAvatarAPI,
  version: remoteVersionAPI,
  template: remoteTemplateAPI,
  pipeline: remotePipelineAPI,
};
