'use client';

import { useState, useCallback, useRef } from 'react';
import { ImagePlus, Loader2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { useEditorStore } from '@/stores/editorStore';
import { MOCK_PIPELINE_RESULT } from '@/data/mock-pipeline-result';
import type { PipelineResult, TemplateName } from '@/types/pipeline';

type Status = 'idle' | 'loading' | 'success' | 'error';

/** Keys accepted by the VRM editor (safety filter) */
const VALID_MORPH_KEYS = new Set([
  'Eye_Width', 'Eye_WidthV', 'Eye_Height', 'Eye_Dist', 'Eye_Rot',
  'Eye_FrontHeight', 'Eye_FrontFlat', 'Eye_TailHeight',
  'Eye_TopLidFlat', 'Eye_LowerLidFlat', 'Eye_TopLidDown', 'Eye_LowerLidUp',
  'Eye_PupilWidth', 'Eye_PupilWidthV',
  'Brow_Dist', 'Brow_Height', 'Brow_Rot', 'Brow_Width', 'Brow_WidthV',
  'Nose_Height', 'Nose_Width', 'Nose_UnderNose',
  'Mouth_Width', 'Mouth_Height', 'Mouth_Corner',
  'Face_JawLine', 'Face_Cheek', 'Face_Roundness', 'Face_ChinWidth',
]);

const TEMPLATE_LABELS: Record<TemplateName, string> = {
  cute: '큐트',
  slim: '슬림',
  mature: '매추어',
};

interface ApplyResult {
  template: TemplateName;
  confidence: number;
  appliedCount: number;
}

export function FaceFeatureApply() {
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<ApplyResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const applyPipelineResult = useEditorStore((s) => s.applyPipelineResult);

  const applyResult = useCallback(
    (pipeline: PipelineResult) => {
      if (pipeline.status !== 'ok' || !pipeline.avatar_parameters) {
        setStatus('error');
        setErrorMsg(pipeline.error ?? '특징 추출에 실패했습니다');
        return;
      }

      // Filter to valid morph keys only
      const filtered: Record<string, number> = {};
      let count = 0;
      for (const [key, value] of Object.entries(pipeline.avatar_parameters)) {
        if (VALID_MORPH_KEYS.has(key)) {
          filtered[key] = value;
          count++;
        }
      }

      applyPipelineResult(filtered);

      setResult({
        template: pipeline.template!,
        confidence: pipeline.confidence!,
        appliedCount: count,
      });
      setStatus('success');
    },
    [applyPipelineResult]
  );

  const processFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith('image/')) {
        setStatus('error');
        setErrorMsg('이미지 파일만 지원합니다 (PNG, JPG, WebP)');
        return;
      }

      // Show preview
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setStatus('loading');
      setResult(null);
      setErrorMsg('');

      try {
        // TODO: Replace with actual API call when server is ready
        // const formData = new FormData();
        // formData.append('image', file);
        // const response = await fetch('/api/pipeline/extract', { method: 'POST', body: formData });
        // const pipeline: PipelineResult = await response.json();

        // Simulate network delay for realistic UX
        await new Promise((resolve) => setTimeout(resolve, 800));
        const pipeline = MOCK_PIPELINE_RESULT;

        applyResult(pipeline);
      } catch (err) {
        console.error('[FaceFeatureApply] Failed:', err);
        setStatus('error');
        setErrorMsg('처리 중 오류가 발생했습니다');
      }
    },
    [applyResult]
  );

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
      e.target.value = '';
    },
    [processFile]
  );

  const handleReset = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setStatus('idle');
    setResult(null);
    setErrorMsg('');
  }, [previewUrl]);

  return (
    <div className="space-y-2">
      <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        얼굴 특징 추출
      </label>

      {/* Drop zone / Preview */}
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
        className={`relative flex flex-col items-center justify-center gap-1.5 px-3 py-4 rounded-lg border border-dashed cursor-pointer transition-all overflow-hidden ${
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
          accept="image/png,image/jpeg,image/webp"
          onChange={handleFileInput}
          className="hidden"
        />

        {previewUrl && (
          <div className="absolute inset-0 opacity-15">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        )}

        <div className="relative z-10 flex flex-col items-center gap-1.5">
          {status === 'loading' ? (
            <>
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <span className="text-[11px] text-muted-foreground">특징 추출 중...</span>
            </>
          ) : previewUrl ? (
            <>
              <Sparkles className="w-5 h-5 text-primary/70" />
              <span className="text-[11px] text-muted-foreground">
                다른 이미지로 교체하려면 클릭
              </span>
            </>
          ) : (
            <>
              <ImagePlus className="w-5 h-5 text-muted-foreground/50" />
              <span className="text-[11px] text-muted-foreground">
                얼굴 사진을 드롭하거나 클릭하여 선택
              </span>
              <span className="text-[10px] text-muted-foreground/50">
                PNG, JPG, WebP
              </span>
            </>
          )}
        </div>
      </div>

      {/* Success result */}
      {status === 'success' && result && (
        <div className="space-y-1.5">
          <div className="flex items-start gap-2 px-2.5 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
            <div className="space-y-0.5 flex-1">
              <p className="text-[11px] text-foreground/80 font-medium">
                {result.appliedCount}개 파라미터 적용 완료
              </p>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                <span>
                  템플릿: {TEMPLATE_LABELS[result.template] ?? result.template}
                </span>
                <span className="text-muted-foreground/40">|</span>
                <span>신뢰도: {(result.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="w-full px-2.5 py-1.5 text-[10px] text-muted-foreground hover:text-foreground rounded-md border border-border/30 hover:bg-accent/30 transition-colors"
          >
            초기화
          </button>
        </div>
      )}

      {/* Error */}
      {status === 'error' && errorMsg && (
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-destructive/10 border border-destructive/20">
          <AlertCircle className="w-3.5 h-3.5 text-destructive shrink-0" />
          <p className="text-[11px] text-destructive/80">{errorMsg}</p>
        </div>
      )}
    </div>
  );
}
