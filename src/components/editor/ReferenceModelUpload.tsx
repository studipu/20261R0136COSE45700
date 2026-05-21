'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, Loader2, CheckCircle2, AlertCircle, Image as ImageIcon } from 'lucide-react';
import { loadVRM } from '@/lib/vrm/loader';
import { detectMaterials } from '@/lib/vrm/materials';
import { recommendHairPreset, recommendHairPresetFromImage } from '@/lib/hair-matching';
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

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp'];
const MODEL_EXTENSIONS = ['.vrm', '.glb'];
const ACCEPTED_EXTENSIONS = [...IMAGE_EXTENSIONS, ...MODEL_EXTENSIONS];

function isImageFile(name: string): boolean {
  const lower = name.toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function isModelFile(name: string): boolean {
  const lower = name.toLowerCase();
  return MODEL_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

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

  function applyRecommendation(recommendation: HairRecommendation) {
    const { bestMatch, extractedColor, confidence } = recommendation;

    const preset = PRESET_ITEMS.find((p) => p.id === bestMatch.presetId);

    setHairFront(preset?.meshUrl ?? null);
    setHairBack(preset?.hairBackUrl ?? null);
    setHairColor(extractedColor);
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

  const processImageFile = useCallback(
    async (file: File) => {
      setStatus('loading');
      setResult(null);
      setErrorMsg('');

      try {
        const recommendation = await recommendHairPresetFromImage(file);

        if (!recommendation) {
          setStatus('error');
          setErrorMsg('이미지에서 헤어 색상을 감지하지 못했습니다');
          return;
        }

        applyRecommendation(recommendation);
        setStatus('success');
      } catch (err) {
        console.error('[ReferenceUpload] Image processing failed:', err);
        setStatus('error');
        setErrorMsg('이미지 분석에 실패했습니다');
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setHairFront, setHairBack, setHairColor, setHairRecommendation],
  );

  const processModelFile = useCallback(
    async (file: File) => {
      setStatus('loading');
      setResult(null);
      setErrorMsg('');

      const blobUrl = URL.createObjectURL(file);

      try {
        const vrm = await loadVRM(blobUrl);
        const materials = detectMaterials(vrm);
        const recommendation = recommendHairPreset(vrm, materials);

        // Dispose VRM scene
        vrm.scene.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.geometry?.dispose();
            const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
            mats.forEach((m) => m?.dispose());
          }
        });

        if (!recommendation) {
          setStatus('error');
          setErrorMsg('헤어 머티리얼을 감지하지 못했습니다');
          return;
        }

        applyRecommendation(recommendation);
        setStatus('success');
      } catch (err) {
        console.error('[ReferenceUpload] Model processing failed:', err);
        setStatus('error');
        setErrorMsg('파일 로드에 실패했습니다');
      } finally {
        URL.revokeObjectURL(blobUrl);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setHairFront, setHairBack, setHairColor, setHairRecommendation],
  );

  const processFile = useCallback(
    async (file: File) => {
      if (isImageFile(file.name)) {
        return processImageFile(file);
      }
      if (isModelFile(file.name)) {
        return processModelFile(file);
      }
      setStatus('error');
      setErrorMsg('지원하지 않는 파일 형식입니다 (이미지 또는 VRM/GLB)');
    },
    [processImageFile, processModelFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
      e.target.value = '';
    },
    [processFile],
  );

  const acceptAttr = ACCEPTED_EXTENSIONS.join(',');

  return (
    <div className="space-y-2">
      <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        레퍼런스 업로드
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
          accept={acceptAttr}
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
            <div className="flex items-center gap-1.5">
              <ImageIcon className="w-4 h-4 text-muted-foreground/50" />
              <Upload className="w-4 h-4 text-muted-foreground/50" />
            </div>
            <span className="text-[11px] text-muted-foreground">
              이미지 또는 VRM/GLB로 헤어 자동 매칭
            </span>
            <span className="text-[9px] text-muted-foreground/50">
              PNG, JPG, WebP, VRM, GLB
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
