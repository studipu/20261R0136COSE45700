'use client';

import { useState } from 'react';
import { getPresetsByCategory, PRESET_ITEMS } from '@/data/presets';
import { useEditorStore } from '@/stores/editorStore';
import { CollapsibleSection } from './CollapsibleSection';
import { Check } from 'lucide-react';
import type { PresetCategory } from '@/types/preset';

interface PresetGridProps {
  selectedPresets?: Record<string, string>; // category → presetId
  onSelectPreset?: (category: PresetCategory, presetId: string) => void;
}

const CATEGORIES: { id: PresetCategory; label: string }[] = [
  { id: 'hair', label: '헤어스타일' },
  { id: 'outfit', label: '의상' },
  { id: 'accessory', label: '악세서리' },
];

export function PresetGrid({ selectedPresets = {}, onSelectPreset }: PresetGridProps) {
  const [selected, setSelected] = useState<Record<string, string>>(selectedPresets);
  const setHairFront = useEditorStore((s) => s.setHairFront);
  const setHairBack = useEditorStore((s) => s.setHairBack);

  const handleSelect = (category: PresetCategory, presetId: string) => {
    setSelected((prev) => ({ ...prev, [category]: presetId }));
    onSelectPreset?.(category, presetId);

    if (category === 'hair') {
      const preset = PRESET_ITEMS.find((p) => p.id === presetId);
      setHairFront(preset?.meshUrl ?? null);
      setHairBack(preset?.hairBackUrl ?? null);
    }
  };

  return (
    <div className="space-y-4">
      {CATEGORIES.map(({ id, label }) => {
        const presets = getPresetsByCategory(id);
        if (presets.length === 0) return null;
        return (
          <CollapsibleSection key={id} title={label} count={presets.length}>
            <div className="grid grid-cols-3 gap-1.5">
              {presets.map((preset) => {
                const isSelected = selected[id] === preset.id;
                return (
                  <button
                    key={preset.id}
                    onClick={() => handleSelect(id, preset.id)}
                    className={`relative rounded-md border p-2 text-center transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/5 ring-1 ring-primary'
                        : 'border-border/50 bg-muted/20 hover:border-border hover:bg-muted/40'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-1 right-1 w-3.5 h-3.5 rounded-full bg-primary flex items-center justify-center">
                        <Check className="w-2 h-2 text-primary-foreground" />
                      </div>
                    )}
                    {/* Placeholder thumbnail */}
                    <div className="w-full aspect-square rounded bg-muted/50 border border-border/30 mb-1 flex items-center justify-center">
                      <span className="text-lg opacity-40">
                        {id === 'hair' ? '💇' : id === 'outfit' ? '👕' : '👓'}
                      </span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">{preset.name}</span>
                  </button>
                );
              })}
            </div>
          </CollapsibleSection>
        );
      })}
    </div>
  );
}
