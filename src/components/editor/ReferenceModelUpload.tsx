'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { loadVRM } from '@/lib/vrm/loader';
import { detectMaterials } from '@/lib/vrm/materials';
import { recommendHairPreset } from '@/lib/hair-matching';
import { PRESET_ITEMS } from '@/data/presets';
import { useEditorStore } from '@/stores/editorStore';
import type { HairRecommendation } from '@/types/editor';
import * as THREE from 'three';

type Status = 'idle' | 'loading' | 'success' | 'error';

interface Result {
  presetName: string;
  confidence: string;
  extractedColor: string;
}

const CONFIDENCE_LABELS: Record<string, string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
};

export function ReferenceModelUpload() {
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<Result | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const setHairFront = useEditorStore((s) => s.setHairFront);
  const setHairBack = useEditorStore((s) => s.setHairBack);
  const setHairColor = useEditorStore((s) => s.setHairColor);
  const setHairRecommendation = useEditorStore((s) => s.setHairRecommendation);

  const processFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith('.vrm') && !file.name.endsWith('.glb')) {
        setStatus('error');
        setErrorMsg('.vrm 또는 .glb 파일만 지원합니다');
        return;
      }

      setStatus('loading');
      setResult(null);
      setErrorMsg('');

      const blobUrl = URL.createObjectURL(file);

      try {
        // 1. Load VRM (temporary, no rendering)
        const vrm = await loadVRM(blobUrl);

        // 2. Detect materials
        const materials = detectMaterials(vrm);

        // 3. Match hair preset
        const recommendation = recommendHairPreset(vrm, materials);

        if (!recommendation || recommendation.confidence === 'low') {
          // Dispose and report
          vrm.scene.traverse((obj) => {
            const mesh = obj as THREE.Mesh;
            if (mesh.isMesh) {
              mesh.geometry?.dispose();
              const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
              mats.forEach((m) => m?.dispose());
            }
          });
          URL.revokeObjectURL(blobUrl);

          if (recommendation) {
            // Low confidence - still apply but warn
            applyRecommendation(recommendation);
            setStatus('success');
          } else {
            setStatus('error');
            setErrorMsg('헤어 머티리얼을 감지하지 못했습니다');
          }
          return;
        }

        // 4. Apply recommendation
        applyRecommendation(recommendation);

        // 5. Dispose VRM scene
        vrm.scene.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.geometry?.dispose();
            const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
            mats.forEach((m) => m?.dispose());
          }
        });

        setStatus('success');
      } catch (err) {
        console.error('[ReferenceUpload] Failed:', err);
        setStatus('error');
        setErrorMsg('파일 로드에 실패했습니다');
      } finally {
        URL.revokeObjectURL(blobUrl);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setHairFront, setHairBack, setHairColor, setHairRecommendation]
  );

  function applyRecommendation(recommendation: HairRecommendation) {
    const { bestMatch, extractedColor, confidence } = recommendation;

    // Find preset data
    const preset = PRESET_ITEMS.find((p) => p.id === bestMatch.presetId);

    // Apply hair GLBs
    setHairFront(preset?.meshUrl ?? null);
    setHairBack(preset?.hairBackUrl ?? null);

    // Apply extracted color
    setHairColor(extractedColor);

    // Store recommendation for PresetGrid badges
    setHairRecommendation(recommendation);

    setResult({
      presetName: preset?.name ?? bestMatch.presetId,
      confidence,
      extractedColor,
    });

    console.log(
      `[ReferenceUpload] Applied: ${preset?.name} (confidence: ${confidence}, color: ${extractedColor})`
    );
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
      // Reset so the same file can be re-uploaded
      e.target.value = '';
    },
    [processFile]
  );

  return (
    <div className="space-y-2">
      <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        참조 모델 업로드
      </label>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragging(false);
        }}
        onClick={() => status !== 'loading' && inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center gap-1.5 px-3 py-4 rounded-lg border border-dashed cursor-pointer transition-all ${
          isDragging
            ? 'border-primary/60 bg-primary/5'
            : status === 'loading'
            ? 'border-border/30 bg-muted/10 cursor-wait'
            : 'border-border/40 bg-muted/10 hover:border-border/60 hover:bg-muted/20'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".vrm,.glb"
          onChange={handleFileInput}
          className="hidden"
        />

        {status === 'loading' ? (
          <>
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
            <span className="text-[11px] text-muted-foreground">분석 중...</span>
          </>
        ) : (
          <>
            <Upload className="w-5 h-5 text-muted-foreground/50" />
            <span className="text-[11px] text-muted-foreground">
              VRM/GLB 파일로 헤어 자동 매칭
            </span>
          </>
        )}
      </div>

      {/* Result message */}
      {status === 'success' && result && (
        <div className="flex items-start gap-2 px-2.5 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="text-[11px] text-foreground/80 font-medium">
              {result.presetName} 적용됨
            </p>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full border border-border/50"
                style={{ backgroundColor: result.extractedColor }}
              />
              <span className="text-[10px] text-muted-foreground">
                신뢰도: {CONFIDENCE_LABELS[result.confidence] ?? result.confidence}
              </span>
            </div>
          </div>
        </div>
      )}

      {status === 'error' && errorMsg && (
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-destructive/10 border border-destructive/20">
          <AlertCircle className="w-3.5 h-3.5 text-destructive shrink-0" />
          <p className="text-[11px] text-destructive/80">{errorMsg}</p>
        </div>
      )}
    </div>
  );
}
