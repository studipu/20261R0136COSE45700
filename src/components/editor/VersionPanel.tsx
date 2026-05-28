'use client';

import { useState, useCallback } from 'react';
import { useEditorStore } from '@/stores/editorStore';
import { useVersionSync } from '@/hooks/useVersionSync';
import { Save, Trash2, RotateCcw, Pencil, Check, X } from 'lucide-react';

interface VersionPanelProps {
  onCaptureScreenshot?: () => Promise<string | undefined>;
}

export function VersionPanel({ onCaptureScreenshot }: VersionPanelProps) {
  const versions = useEditorStore((s) => s.versions);
  const restoreVersion = useEditorStore((s) => s.restoreVersion);
  const { syncSaveVersion, syncDeleteVersion, syncRenameVersion } = useVersionSync();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [compareId, setCompareId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      let thumbnail: string | undefined;
      if (onCaptureScreenshot) {
        thumbnail = await onCaptureScreenshot();
      }
      await syncSaveVersion(undefined, thumbnail);
    } finally {
      setIsSaving(false);
    }
  }, [syncSaveVersion, onCaptureScreenshot]);

  const handleStartRename = (id: string, currentName: string) => {
    setEditingId(id);
    setEditName(currentName);
  };

  const handleConfirmRename = () => {
    if (editingId && editName.trim()) {
      syncRenameVersion(editingId, editName.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = () => {
    setEditingId(null);
  };

  return (
    <div className="space-y-3">
      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={isSaving}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        <Save className="w-3.5 h-3.5" />
        {isSaving ? '저장 중...' : '현재 상태 저장'}
      </button>

      <div className="text-[11px] text-muted-foreground/60 text-center">
        {versions.length}/5 버전 사용 중
      </div>

      {/* Version list */}
      {versions.length === 0 ? (
        <div className="rounded-lg border border-border/50 bg-muted/30 p-4 text-center">
          <p className="text-xs text-muted-foreground">저장된 버전이 없습니다</p>
          <p className="text-[11px] text-muted-foreground/60 mt-1">
            Ctrl+S 로 빠르게 저장할 수 있습니다
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {[...versions].reverse().map((version) => (
            <div
              key={version.id}
              className={`rounded-lg border p-2.5 transition-colors ${
                compareId === version.id
                  ? 'border-primary bg-primary/5'
                  : 'border-border/50 bg-muted/20 hover:border-border'
              }`}
            >
              <div className="flex gap-2">
                {/* Thumbnail */}
                <div className="w-16 h-16 rounded bg-muted/50 border border-border/30 shrink-0 overflow-hidden">
                  {version.thumbnailDataUrl ? (
                    <img
                      src={version.thumbnailDataUrl}
                      alt={version.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[10px] text-muted-foreground/40">
                      No preview
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  {editingId === version.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleConfirmRename();
                          if (e.key === 'Escape') handleCancelRename();
                        }}
                        className="flex-1 px-1.5 py-0.5 text-xs bg-background border border-border rounded text-foreground"
                        autoFocus
                      />
                      <button onClick={handleConfirmRename} className="p-0.5 text-primary hover:text-primary/80">
                        <Check className="w-3 h-3" />
                      </button>
                      <button onClick={handleCancelRename} className="p-0.5 text-muted-foreground hover:text-foreground">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <h4 className="text-xs font-medium text-foreground truncate">{version.name}</h4>
                  )}
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                    {new Date(version.createdAt).toLocaleString('ko-KR', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>

                  {/* Actions */}
                  <div className="flex gap-1 mt-1.5">
                    <button
                      onClick={() => restoreVersion(version.id)}
                      className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 transition-colors"
                      title="이 버전으로 복원"
                    >
                      <RotateCcw className="w-2.5 h-2.5" />
                      복원
                    </button>
                    <button
                      onClick={() => setCompareId(compareId === version.id ? null : version.id)}
                      className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
                        compareId === version.id
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                      }`}
                      title="비교용으로 선택"
                    >
                      비교
                    </button>
                    <button
                      onClick={() => handleStartRename(version.id, version.name)}
                      className="p-0.5 text-muted-foreground hover:text-foreground transition-colors"
                      title="이름 변경"
                    >
                      <Pencil className="w-2.5 h-2.5" />
                    </button>
                    <button
                      onClick={() => syncDeleteVersion(version.id)}
                      className="p-0.5 text-muted-foreground hover:text-destructive transition-colors"
                      title="삭제"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
