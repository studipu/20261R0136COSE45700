'use client';

import { useState } from 'react';
import { useEditorStore } from '@/stores/editorStore';
import { QUICK_PRESETS } from '@/data/presets';
import type { QuickPreset } from '@/types/preset';
import { Sparkles, Plus, Save, X } from 'lucide-react';

export function QuickPresets() {
  const setMorphTarget = useEditorStore((s) => s.setMorphTarget);
  const morphTargets = useEditorStore((s) => s.morphTargets);
  const [customPresets, setCustomPresets] = useState<QuickPreset[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem('avatar-editor-custom-presets');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');

  const applyPreset = (preset: QuickPreset) => {
    if (preset.values.morphTargets) {
      for (const [name, value] of Object.entries(preset.values.morphTargets)) {
        setMorphTarget(name, value);
      }
    }
  };

  const saveCustomPreset = () => {
    if (!newPresetName.trim()) return;
    const preset: QuickPreset = {
      id: `custom-${Date.now()}`,
      name: newPresetName.trim(),
      isBuiltIn: false,
      values: { morphTargets: { ...morphTargets } },
    };
    const updated = [...customPresets, preset];
    setCustomPresets(updated);
    try {
      localStorage.setItem('avatar-editor-custom-presets', JSON.stringify(updated));
    } catch { /* ignore */ }
    setShowSaveDialog(false);
    setNewPresetName('');
  };

  const deleteCustomPreset = (id: string) => {
    const updated = customPresets.filter((p) => p.id !== id);
    setCustomPresets(updated);
    try {
      localStorage.setItem('avatar-editor-custom-presets', JSON.stringify(updated));
    } catch { /* ignore */ }
  };

  const allPresets = [...QUICK_PRESETS, ...customPresets];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          빠른 프리셋
        </h3>
        <button
          onClick={() => setShowSaveDialog(true)}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded hover:border-border transition-colors"
        >
          <Plus className="w-2.5 h-2.5" />
          저장
        </button>
      </div>

      {/* Save dialog */}
      {showSaveDialog && (
        <div className="flex items-center gap-1.5 p-2 bg-muted/30 rounded-md border border-border/50">
          <input
            type="text"
            value={newPresetName}
            onChange={(e) => setNewPresetName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') saveCustomPreset();
              if (e.key === 'Escape') setShowSaveDialog(false);
            }}
            placeholder="프리셋 이름..."
            className="flex-1 px-2 py-1 text-xs bg-background border border-border rounded text-foreground"
            autoFocus
          />
          <button
            onClick={saveCustomPreset}
            className="p-1 text-primary hover:text-primary/80"
          >
            <Save className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setShowSaveDialog(false)}
            className="p-1 text-muted-foreground hover:text-foreground"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Preset chips */}
      <div className="flex flex-wrap gap-1.5">
        {allPresets.map((preset) => (
          <div key={preset.id} className="group relative">
            <button
              onClick={() => applyPreset(preset)}
              className="px-2.5 py-1.5 text-[11px] bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors border border-border/30"
              title={preset.description}
            >
              {preset.name}
            </button>
            {!preset.isBuiltIn && (
              <button
                onClick={() => deleteCustomPreset(preset.id)}
                className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-destructive text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-2 h-2" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
