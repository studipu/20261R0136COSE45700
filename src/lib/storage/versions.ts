import type { AvatarVersion } from '@/types/editor';

const STORAGE_PREFIX = 'avatar-editor-versions';
const MAX_VERSIONS = 5;

export function loadVersions(modelName: string): AvatarVersion[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}-${modelName}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveVersions(modelName: string, versions: AvatarVersion[]): void {
  if (typeof window === 'undefined') return;
  try {
    // Enforce max versions
    const trimmed = versions.slice(-MAX_VERSIONS);
    localStorage.setItem(`${STORAGE_PREFIX}-${modelName}`, JSON.stringify(trimmed));
  } catch (e) {
    console.warn('Failed to save versions to localStorage:', e);
  }
}

export function deleteVersionStorage(modelName: string): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(`${STORAGE_PREFIX}-${modelName}`);
}
