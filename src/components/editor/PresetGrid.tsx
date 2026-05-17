'use client';

import { useState } from 'react';
import { getPresetsByCategory, PRESET_ITEMS } from '@/data/presets';
import { useEditorStore } from '@/stores/editorStore';
import { CollapsibleSection } from './CollapsibleSection';
import { Check, Sparkles } from 'lucide-react';
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
  const setOutfit = useEditorStore((s) => s.setOutfit);
  const hairRecommendation = useEditorStore((s) => s.hairRecommendation);

  const handleSelect = (category: PresetCategory, presetId: string) => {
    setSelected((prev) => ({ ...prev, [category]: presetId }));
    onSelectPreset?.(category, presetId);

    const preset = PRESET_ITEMS.find((p) => p.id === presetId);
    if (category === 'hair') {
      setHairFront(preset?.meshUrl ?? null);
      setHairBack(preset?.hairBackUrl ?? null);
    } else if (category === 'outfit') {
      setOutfit(preset?.meshUrl ?? null);
    }
  };

  // Determine if a preset is the recommended one
  const bestMatchId = hairRecommendation?.confidence !== 'low' ? hairRecommendation?.bestMatch.presetId : null;
  const matchResultMap = hairRecommendation?.allResults.reduce<Record<string, number>>((acc, r) => {
    acc[r.presetId] = Math.round(r.colorScore * 100);
    return acc;
  }, {}) ?? {};

  return (
    <div className="space-y-4">
      {/* Extracted color indicator */}
      {hairRecommendation && hairRecommendation.confidence !== 'low' && (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-accent/30 border border-border/30">
          <div
            className="w-4 h-4 rounded-full border border-border/50 shrink-0"
            style={{ backgroundColor: hairRecommendation.extractedColor }}
            title={`VRM 헤어 색상: ${hairRecommendation.extractedColor}`}
          />
          <span className="text-[10px] text-muted-foreground">
            감지된 헤어 색상으로 자동 추천
          </span>
        </div>
      )}

      {CATEGORIES.map(({ id, label }) => {
        const presets = getPresetsByCategory(id);
        if (presets.length === 0) return null;
        return (
          <CollapsibleSection key={id} title={label} count={presets.length}>
            <div className="grid grid-cols-3 gap-1.5">
              {presets.map((preset) => {
                const isSelected = selected[id] === preset.id;
                const isRecommended = id === 'hair' && preset.id === bestMatchId;
                const colorPercent = id === 'hair' ? matchResultMap[preset.id] : undefined;
                return (
                  <button
                    key={preset.id}
                    onClick={() => handleSelect(id, preset.id)}
                    className={`relative rounded-md border p-2 text-center transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/5 ring-1 ring-primary'
                        : isRecommended
                        ? 'border-amber-400/60 bg-amber-400/5 ring-1 ring-amber-400/40'
                        : 'border-border/50 bg-muted/20 hover:border-border hover:bg-muted/40'
                    }`}
                    title={colorPercent !== undefined ? `색상 유사도: ${colorPercent}%` : undefined}
                  >
                    {isSelected && (
                      <div className="absolute top-1 right-1 w-3.5 h-3.5 rounded-full bg-primary flex items-center justify-center">
                        <Check className="w-2 h-2 text-primary-foreground" />
                      </div>
                    )}
                    {isRecommended && !isSelected && (
                      <div className="absolute top-1 right-1 flex items-center gap-0.5 px-1 py-0.5 rounded-full bg-amber-400/90 text-[8px] font-bold text-amber-950">
                        <Sparkles className="w-2 h-2" />
                        추천
                      </div>
                    )}
                    <div className="w-full aspect-square rounded bg-muted/50 border border-border/30 mb-1 flex items-center justify-center overflow-hidden">
                      {preset.thumbnailUrl ? (
                        <img
                          src={preset.thumbnailUrl}
                          alt={preset.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-lg opacity-40">
                          {id === 'hair' ? '💇' : id === 'outfit' ? '👕' : '👓'}
                        </span>
                      )}
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
