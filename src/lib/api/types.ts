import type { AvatarParameters, AvatarVersion } from '@/types/editor';
import type { TemplateMetadata } from '@/types/template';

export interface SaveAvatarRequest {
  avatarId: string;
  templateId: string;
  parameters: AvatarParameters;
}

export interface AvatarRecord {
  avatarId: string;
  templateId: string;
  parameters: AvatarParameters;
  updatedAt: string;
}

export interface AvatarAPI {
  saveAvatar(data: SaveAvatarRequest): Promise<AvatarRecord>;
  loadAvatar(avatarId: string): Promise<AvatarRecord | null>;
  listAvatars(): Promise<AvatarRecord[]>;
  deleteAvatar(avatarId: string): Promise<void>;
}

export interface VersionAPI {
  saveVersion(avatarId: string, version: AvatarVersion): Promise<void>;
  listVersions(avatarId: string): Promise<AvatarVersion[]>;
  deleteVersion(avatarId: string, versionId: string): Promise<void>;
  updateVersion(avatarId: string, versionId: string, updates: Partial<Pick<AvatarVersion, 'name'>>): Promise<void>;
}

export interface TemplateAPI {
  listTemplates(): Promise<TemplateMetadata[]>;
  getTemplate(templateId: string): Promise<TemplateMetadata | null>;
}

export interface APIClient {
  avatar: AvatarAPI;
  version: VersionAPI;
  template: TemplateAPI;
}
