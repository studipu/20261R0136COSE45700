import type { APIClient, AvatarAPI, VersionAPI, TemplateAPI, PipelineAPI, SaveAvatarRequest, AvatarRecord } from './types';
import type { AvatarVersion } from '@/types/editor';
import type { TemplateMetadata } from '@/types/template';
import { TEMPLATES } from '@/data/templates';

const STORAGE_PREFIX = 'avatar-editor';

function getKey(scope: string, id?: string): string {
  return id ? `${STORAGE_PREFIX}-${scope}-${id}` : `${STORAGE_PREFIX}-${scope}`;
}

function safeGet<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function safeSet(key: string, value: unknown): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn('localStorage write failed:', e);
  }
}

function safeRemove(key: string): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(key);
}

// --- Avatar API (localStorage) ---

const localAvatarAPI: AvatarAPI = {
  async saveAvatar(data: SaveAvatarRequest): Promise<AvatarRecord> {
    const record: AvatarRecord = {
      ...data,
      updatedAt: new Date().toISOString(),
    };
    safeSet(getKey('avatar', data.avatarId), record);

    // Update index
    const index = safeGet<string[]>(getKey('avatar-index')) ?? [];
    if (!index.includes(data.avatarId)) {
      index.push(data.avatarId);
      safeSet(getKey('avatar-index'), index);
    }
    return record;
  },

  async loadAvatar(avatarId: string): Promise<AvatarRecord | null> {
    return safeGet<AvatarRecord>(getKey('avatar', avatarId));
  },

  async listAvatars(): Promise<AvatarRecord[]> {
    const index = safeGet<string[]>(getKey('avatar-index')) ?? [];
    const records: AvatarRecord[] = [];
    for (const id of index) {
      const record = safeGet<AvatarRecord>(getKey('avatar', id));
      if (record) records.push(record);
    }
    return records;
  },

  async deleteAvatar(avatarId: string): Promise<void> {
    safeRemove(getKey('avatar', avatarId));
    const index = safeGet<string[]>(getKey('avatar-index')) ?? [];
    safeSet(getKey('avatar-index'), index.filter((id) => id !== avatarId));
    // Also delete versions
    safeRemove(getKey('versions', avatarId));
  },
};

// --- Version API (localStorage) ---

const MAX_VERSIONS = 5;

const localVersionAPI: VersionAPI = {
  async saveVersion(avatarId: string, version: AvatarVersion): Promise<void> {
    const versions = safeGet<AvatarVersion[]>(getKey('versions', avatarId)) ?? [];
    versions.push(version);
    // Keep max 5
    while (versions.length > MAX_VERSIONS) {
      versions.shift();
    }
    safeSet(getKey('versions', avatarId), versions);
  },

  async listVersions(avatarId: string): Promise<AvatarVersion[]> {
    return safeGet<AvatarVersion[]>(getKey('versions', avatarId)) ?? [];
  },

  async deleteVersion(avatarId: string, versionId: string): Promise<void> {
    const versions = safeGet<AvatarVersion[]>(getKey('versions', avatarId)) ?? [];
    safeSet(getKey('versions', avatarId), versions.filter((v) => v.id !== versionId));
  },

  async updateVersion(avatarId: string, versionId: string, updates: Partial<Pick<AvatarVersion, 'name'>>): Promise<void> {
    const versions = safeGet<AvatarVersion[]>(getKey('versions', avatarId)) ?? [];
    const idx = versions.findIndex((v) => v.id === versionId);
    if (idx !== -1) {
      versions[idx] = { ...versions[idx], ...updates };
      safeSet(getKey('versions', avatarId), versions);
    }
  },
};

// --- Template API (static data) ---

const localTemplateAPI: TemplateAPI = {
  async listTemplates(): Promise<TemplateMetadata[]> {
    return TEMPLATES;
  },

  async getTemplate(templateId: string): Promise<TemplateMetadata | null> {
    return TEMPLATES.find((t) => t.id === templateId) ?? null;
  },
};

// --- Combined Client ---

const localPipelineAPI: PipelineAPI = {
  async extractFeatures(_imageFile: File) {
    // TODO: Replace with actual HTTP call when server is ready
    const { MOCK_PIPELINE_RESULT } = await import('@/data/mock-pipeline-result');
    return MOCK_PIPELINE_RESULT;
  },
};

export const localAPIClient: APIClient = {
  avatar: localAvatarAPI,
  version: localVersionAPI,
  template: localTemplateAPI,
  pipeline: localPipelineAPI,
};
