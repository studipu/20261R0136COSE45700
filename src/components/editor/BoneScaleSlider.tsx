'use client';

import { useCallback } from 'react';
import { Slider } from '@/components/ui/slider';
import { useEditorStore } from '@/stores/editorStore';
import { RotateCcw } from 'lucide-react';

interface BoneScaleSliderProps {
  boneName: string;
  axis: 'x' | 'y' | 'z';
  label: string;
  min?: number;
  max?: number;
}

export function BoneScaleSlider({ boneName, axis, label, min = 0.5, max = 2.0 }: BoneScaleSliderProps) {
  const value = useEditorStore((s) => s.boneScales[boneName]?.[axis] ?? 1.0);
  const setBoneScale = useEditorStore((s) => s.setBoneScale);

  const isModified = Math.abs(value - 1.0) > 0.01;

  const handleReset = useCallback(() => {
    setBoneScale(boneName, axis, 1.0);
  }, [boneName, axis, setBoneScale]);

  return (
    <div className="group space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span
          className={`truncate max-w-[160px] transition-colors ${
            isModified ? 'text-foreground font-medium' : 'text-muted-foreground'
          }`}
          title={`${boneName}.${axis}`}
        >
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          <span
            className={`font-mono text-[11px] w-10 text-right tabular-nums transition-colors ${
              isModified ? 'text-primary' : 'text-muted-foreground/60'
            }`}
          >
            {value.toFixed(2)}
          </span>
          {isModified && (
            <button
              onClick={handleReset}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-accent"
              title="초기화"
            >
              <RotateCcw className="w-3 h-3 text-muted-foreground" />
            </button>
          )}
        </div>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={0.01}
        onValueChange={(val) => setBoneScale(boneName, axis, Array.isArray(val) ? val[0] : val)}
      />
    </div>
  );
}
