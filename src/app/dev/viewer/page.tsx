'use client';

import dynamic from 'next/dynamic';
import { useState, useCallback, useRef, useMemo } from 'react';
import { WebGLCheck } from '@/components/viewer/WebGLCheck';
import { MorphTargetSlider } from '@/components/editor/MorphTargetSlider';
import { BoneScaleSlider } from '@/components/editor/BoneScaleSlider';
import { CollapsibleSection } from '@/components/editor/CollapsibleSection';
import { MaterialEditor } from '@/components/editor/MaterialEditor';
import { VersionPanel } from '@/components/editor/VersionPanel';
import { TemplateSelector } from '@/components/editor/TemplateSelector';
import { PresetGrid } from '@/components/editor/PresetGrid';
import { SliderSearch } from '@/components/editor/SliderSearch';
import { QuickPresets } from '@/components/editor/QuickPresets';
import { ViewerToolbar } from '@/components/viewer/ViewerToolbar';
import { useEditorStore } from '@/stores/editorStore';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useCanvasScreenshot } from '@/hooks/useCanvasScreenshot';
import type { DetectedMaterial } from '@/lib/vrm/materials';
import type { TemplateMetadata } from '@/types/template';
import {
  User,
  Smile,
  SlidersHorizontal,
  Palette,
  Shirt,
  Upload,
  PanelLeftClose,
  PanelLeft,
  RotateCcw,
  History,
  LayoutTemplate,
  Undo2,
  Redo2,
  Sparkles,
  Box,
} from 'lucide-react';
import type { ThreeJSViewerHandle } from '@/components/viewer/ThreeJSViewer';

const ThreeJSViewer = dynamic(
  () => import('@/components/viewer/ThreeJSViewer').then((m) => ({ default: m.ThreeJSViewer })),
  { ssr: false }
);

const DEFAULT_MODEL_URL = '/models/CustomizableCharacter.vrm';

const BONE_SCALE_PRESETS: { boneName: string; label: string; axes: ('x' | 'y' | 'z')[] }[] = [
  { boneName: 'head', label: '머리', axes: ['x', 'y', 'z'] },
  { boneName: 'neck', label: '목', axes: ['x', 'y', 'z'] },
  { boneName: 'chest', label: '가슴', axes: ['x', 'y', 'z'] },
  { boneName: 'spine', label: '허리', axes: ['x', 'y', 'z'] },
  { boneName: 'hips', label: '골반', axes: ['x', 'y', 'z'] },
  { boneName: 'leftUpperArm', label: '왼팔(상)', axes: ['x', 'y', 'z'] },
  { boneName: 'rightUpperArm', label: '오른팔(상)', axes: ['x', 'y', 'z'] },
  { boneName: 'leftUpperLeg', label: '왼다리(상)', axes: ['x', 'y', 'z'] },
  { boneName: 'rightUpperLeg', label: '오른다리(상)', axes: ['x', 'y', 'z'] },
];

const MORPH_LABELS: Record<string, string> = {
  face_eye_size: '눈 크기',
  face_eye_width: '눈 가로폭',
  face_eye_height: '눈 세로폭',
  face_eye_tilt: '눈매 각도',
  face_eye_spacing: '눈 간격',
  face_nose_height: '코 높이',
  face_nose_width: '코 너비',
  face_nose_length: '코 길이',
  face_jaw_width: '턱 너비',
  face_jaw_length: '턱 길이',
  face_chin_shape: '턱 끝 형태',
  face_cheek_fullness: '볼 볼륨',
  face_lip_thickness: '입술 두께',
  face_lip_width: '입 너비',
  face_forehead_height: '이마 높이',
  face_forehead_width: '이마 너비',
  face_eyebrow_height: '눈썹 높이',
  face_eyebrow_thickness: '눈썹 두께',
  body_shoulder_width: '어깨 너비',
  body_chest_size: '가슴 크기',
  body_waist_width: '허리 너비',
  body_hip_width: '골반 너비',
  body_arm_thickness: '팔 굵기',
  body_leg_thickness: '다리 굵기',
};

const AXIS_LABELS: Record<string, string> = { x: '가로', y: '세로', z: '깊이' };

type TabId = 'face' | 'body' | 'expressions' | 'material' | 'style' | 'version';

const TAB_CONFIG: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'face', label: '얼굴', icon: User },
  { id: 'body', label: '체형', icon: SlidersHorizontal },
  { id: 'expressions', label: '표정', icon: Smile },
  { id: 'material', label: '재질', icon: Palette },
  { id: 'style', label: '스타일', icon: Shirt },
  { id: 'version', label: '버전', icon: History },
];

export default function DevViewerPage() {
  const [modelUrl, setModelUrl] = useState(DEFAULT_MODEL_URL);
  const [modelName, setModelName] = useState('CustomizableCharacter.vrm');
  const [expressionNames, setExpressionNames] = useState<string[]>([]);
  const [morphTargetNames, setMorphTargetNames] = useState<string[]>([]);
  const [availableBones, setAvailableBones] = useState<string[]>([]);
  const [detectedMaterials, setDetectedMaterials] = useState<DetectedMaterial[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>('face');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showModifiedOnly, setShowModifiedOnly] = useState(false);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [currentTemplateId, setCurrentTemplateId] = useState<string | null>('customizable-default');
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const isResizing = useRef(false);

  const resetAll = useEditorStore((s) => s.resetAll);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const canUndo = useEditorStore((s) => s.canUndo);
  const canRedo = useEditorStore((s) => s.canRedo);
  const saveVersion = useEditorStore((s) => s.saveVersion);
  const morphTargets = useEditorStore((s) => s.morphTargets);
  const boneScales = useEditorStore((s) => s.boneScales);
  const viewerRef = useRef<ThreeJSViewerHandle>(null);
  const { capture } = useCanvasScreenshot();

  const handleModelLoaded = useCallback(
    (
      expressions: string[],
      morphs: string[],
      bones: string[],
      materials: DetectedMaterial[]
    ) => {
      setExpressionNames(expressions);
      setMorphTargetNames(morphs);
      setAvailableBones(bones);
      setDetectedMaterials(materials);
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && (file.name.endsWith('.vrm') || file.name.endsWith('.glb'))) {
        const url = URL.createObjectURL(file);
        resetAll();
        setExpressionNames([]);
        setMorphTargetNames([]);
        setAvailableBones([]);
        setDetectedMaterials([]);
        setModelUrl(url);
        setModelName(file.name);
      }
    },
    [resetAll]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleTemplateSelect = useCallback(
    (template: TemplateMetadata) => {
      resetAll();
      setExpressionNames([]);
      setMorphTargetNames([]);
      setAvailableBones([]);
      setDetectedMaterials([]);
      setModelUrl(template.vrmUrl);
      setModelName(template.name);
      setCurrentTemplateId(template.id);
      setShowTemplateSelector(false);
    },
    [resetAll]
  );

  const handleCaptureScreenshot = useCallback(async () => {
    return capture(128);
  }, [capture]);

  const handleSaveVersion = useCallback(async () => {
    const thumbnail = await capture(128);
    saveVersion(undefined, thumbnail);
  }, [capture, saveVersion]);

  // Sidebar resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    const startX = e.clientX;
    const startWidth = sidebarWidth;
    const handleMove = (ev: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = Math.max(300, Math.min(480, startWidth + ev.clientX - startX));
      setSidebarWidth(newWidth);
    };
    const handleUp = () => {
      isResizing.current = false;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [sidebarWidth]);

  // Keyboard shortcuts
  useKeyboardShortcuts(
    useMemo(
      () => ({
        onUndo: undo,
        onRedo: redo,
        onSave: handleSaveVersion,
        onResetCamera: () => viewerRef.current?.resetCamera(),
        onToggleGrid: () => setShowGrid((g) => !g),
        onToggleSidebar: () => setSidebarOpen((o) => !o),
        onSwitchTab: (index: number) => {
          if (index >= 0 && index < TAB_CONFIG.length) {
            setActiveTab(TAB_CONFIG[index].id);
          }
        },
      }),
      [undo, redo, handleSaveVersion]
    )
  );

  // Filter morphs
  const faceMorphs = morphTargetNames.filter((n) => n.startsWith('face_'));
  const bodyMorphs = morphTargetNames.filter((n) => n.startsWith('body_'));
  const expressionSet = new Set(expressionNames);
  const otherMorphs = morphTargetNames.filter(
    (n) => !n.startsWith('face_') && !n.startsWith('body_') && !expressionSet.has(n)
  );

  const availablePresets = BONE_SCALE_PRESETS.filter((p) => availableBones.includes(p.boneName));

  // Search & filter
  const filterMorphs = useCallback(
    (names: string[]) => {
      let filtered = names;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter((n) => {
          const label = MORPH_LABELS[n] ?? n;
          return label.toLowerCase().includes(q) || n.toLowerCase().includes(q);
        });
      }
      if (showModifiedOnly) {
        filtered = filtered.filter((n) => (morphTargets[n] ?? 0) !== 0);
      }
      return filtered;
    },
    [searchQuery, showModifiedOnly, morphTargets]
  );

  const modifiedMorphCount = morphTargetNames.filter((n) => (morphTargets[n] ?? 0) !== 0).length;
  const modifiedBoneCount = Object.keys(boneScales).length;

  const tabCounts: Record<string, number> = {
    face: faceMorphs.length,
    body: availablePresets.length + bodyMorphs.length,
    expressions: expressionNames.length + otherMorphs.length,
    material: detectedMaterials.length,
    style: 0,
    version: useEditorStore.getState().versions.length,
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ===== Sidebar ===== */}
      <div
        className="flex flex-col border-r border-border/50 bg-card/80 backdrop-blur-md transition-all duration-300 relative shrink-0 z-20"
        style={{ width: sidebarOpen ? sidebarWidth : 0 }}
      >
        {sidebarOpen && (
          <>
            {/* --- Branding Header --- */}
            <div className="px-4 py-4 border-b border-border/50 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/80 to-primary/40 flex items-center justify-center shadow-lg glow-primary">
                    <Box className="w-4 h-4 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-sm font-bold text-foreground tracking-tight">
                      Avatar Studio
                    </h1>
                    <p className="text-[10px] text-muted-foreground/70 font-medium tracking-wide uppercase">
                      Character Designer
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
                  title="패널 닫기 (S)"
                >
                  <PanelLeftClose className="w-4 h-4" />
                </button>
              </div>

              {/* Model info + Undo/Redo bar */}
              <div className="flex items-center justify-between mt-3 gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <div className="w-6 h-6 rounded-md bg-accent/50 flex items-center justify-center shrink-0">
                    <Sparkles className="w-3 h-3 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[11px] text-foreground/80 font-medium truncate" title={modelName}>
                      {modelName}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-0.5 shrink-0">
                  <button
                    onClick={() => setShowTemplateSelector(!showTemplateSelector)}
                    className="px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:border-primary/30 hover:bg-accent/30 transition-all"
                    title="템플릿 선택"
                  >
                    <LayoutTemplate className="w-3 h-3" />
                  </button>
                  <div className="w-px h-4 bg-border/50 mx-1" />
                  <button
                    onClick={undo}
                    disabled={!canUndo()}
                    className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 disabled:opacity-20 disabled:hover:bg-transparent transition-all"
                    title="실행 취소 (Ctrl+Z)"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={redo}
                    disabled={!canRedo()}
                    className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 disabled:opacity-20 disabled:hover:bg-transparent transition-all"
                    title="다시 실행 (Ctrl+Shift+Z)"
                  >
                    <Redo2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Template selector (overlay) */}
            {showTemplateSelector && (
              <div className="px-4 py-3 border-b border-border/50 bg-accent/20 shrink-0">
                <TemplateSelector
                  currentTemplateId={currentTemplateId}
                  onSelect={handleTemplateSelect}
                />
              </div>
            )}

            {/* --- Tabs --- */}
            <div className="flex border-b border-border/50 shrink-0 overflow-x-auto scrollbar-none bg-card/50">
              {TAB_CONFIG.map((tab, index) => {
                const Icon = tab.icon;
                const count = tabCounts[tab.id] || 0;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center justify-center gap-1 px-2.5 py-2.5 text-[11px] font-medium transition-all relative whitespace-nowrap shrink-0 ${
                      isActive
                        ? 'text-primary'
                        : 'text-muted-foreground/70 hover:text-foreground'
                    }`}
                    title={`${tab.label} (${index + 1})`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'drop-shadow-[0_0_4px_oklch(0.7_0.18_270/40%)]' : ''}`} />
                    <span>{tab.label}</span>
                    {count > 0 && (
                      <span
                        className={`text-[9px] min-w-[16px] text-center px-1 py-0.5 rounded-full font-medium ${
                          isActive
                            ? 'bg-primary/15 text-primary'
                            : 'bg-muted/60 text-muted-foreground/60'
                        }`}
                      >
                        {count}
                      </span>
                    )}
                    {isActive && (
                      <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-full shadow-[0_0_8px_oklch(0.7_0.18_270/50%)]" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* --- Search & Reset (morph tabs only) --- */}
            {['face', 'body', 'expressions'].includes(activeTab) && (
              <div className="px-4 py-3 border-b border-border/50 shrink-0 space-y-2">
                <SliderSearch
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  showModifiedOnly={showModifiedOnly}
                  onToggleModifiedOnly={() => setShowModifiedOnly(!showModifiedOnly)}
                  modifiedCount={modifiedMorphCount + modifiedBoneCount}
                />
                <button
                  onClick={resetAll}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent/50 text-muted-foreground rounded-lg hover:bg-accent hover:text-foreground transition-colors border border-border/30"
                >
                  <RotateCcw className="w-3 h-3" />
                  전체 초기화
                </button>
              </div>
            )}

            {/* --- Tab Content --- */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
              {/* Loading state */}
              {availableBones.length === 0 && expressionNames.length === 0 && !['version', 'style'].includes(activeTab) && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/30 flex items-center justify-center mb-4 animate-pulse">
                    <Upload className="w-6 h-6 text-primary/60" />
                  </div>
                  <p className="text-sm font-medium text-foreground/60">
                    모델 로드 중...
                  </p>
                  <p className="text-[11px] text-muted-foreground/50 mt-1.5 max-w-[200px]">
                    VRM 파일이 로드되면 편집 옵션이 표시됩니다
                  </p>
                </div>
              )}

              {/* Face Tab */}
              {activeTab === 'face' && (
                <>
                  <QuickPresets />
                  {filterMorphs(faceMorphs).length > 0 ? (
                    <CollapsibleSection title="얼굴 형태" count={filterMorphs(faceMorphs).length}>
                      {filterMorphs(faceMorphs).map((name) => (
                        <MorphTargetSlider
                          key={name}
                          name={name}
                          label={MORPH_LABELS[name] || name}
                        />
                      ))}
                    </CollapsibleSection>
                  ) : (
                    availableBones.length > 0 && !searchQuery && !showModifiedOnly && (
                      <div className="rounded-xl border border-border/30 bg-accent/20 p-4">
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          이 모델에는 얼굴 편집용 morph target(face_*)이 없습니다.
                          Blender에서 Shape Key를 추가한 VRM 모델을 드롭하여 테스트하세요.
                        </p>
                      </div>
                    )
                  )}
                </>
              )}

              {/* Body Tab */}
              {activeTab === 'body' && (
                <>
                  {filterMorphs(bodyMorphs).length > 0 && (
                    <CollapsibleSection title="체형 Morph" count={filterMorphs(bodyMorphs).length}>
                      {filterMorphs(bodyMorphs).map((name) => (
                        <MorphTargetSlider
                          key={name}
                          name={name}
                          label={MORPH_LABELS[name] || name}
                        />
                      ))}
                    </CollapsibleSection>
                  )}
                  {availablePresets.length > 0 && (
                    <CollapsibleSection title="본 스케일" count={availablePresets.length}>
                      {availablePresets.map((preset) => (
                        <div key={preset.boneName} className="space-y-2">
                          <h4 className="text-xs font-medium text-foreground/70 pt-1 first:pt-0">
                            {preset.label}
                          </h4>
                          <div className="space-y-2 pl-3 border-l-2 border-primary/20">
                            {preset.axes.map((axis) => (
                              <BoneScaleSlider
                                key={`${preset.boneName}-${axis}`}
                                boneName={preset.boneName}
                                axis={axis}
                                label={AXIS_LABELS[axis]}
                                min={0.2}
                                max={3.0}
                              />
                            ))}
                          </div>
                        </div>
                      ))}
                    </CollapsibleSection>
                  )}
                </>
              )}

              {/* Expressions Tab */}
              {activeTab === 'expressions' && (
                <>
                  {filterMorphs(expressionNames).length > 0 && (
                    <CollapsibleSection title="표정" count={filterMorphs(expressionNames).length}>
                      {filterMorphs(expressionNames).map((name) => (
                        <MorphTargetSlider key={`expr-${name}`} name={name} />
                      ))}
                    </CollapsibleSection>
                  )}
                  {filterMorphs(otherMorphs).length > 0 && (
                    <CollapsibleSection
                      title="기타 Morph Targets"
                      count={filterMorphs(otherMorphs).length}
                      defaultOpen={false}
                    >
                      {filterMorphs(otherMorphs).map((name) => (
                        <MorphTargetSlider key={`morph-${name}`} name={name} />
                      ))}
                    </CollapsibleSection>
                  )}
                </>
              )}

              {/* Material Tab */}
              {activeTab === 'material' && (
                <MaterialEditor detectedMaterials={detectedMaterials} />
              )}

              {/* Style Tab */}
              {activeTab === 'style' && (
                <PresetGrid />
              )}

              {/* Version Tab */}
              {activeTab === 'version' && (
                <VersionPanel onCaptureScreenshot={handleCaptureScreenshot} />
              )}
            </div>

            {/* --- Bottom Status Bar --- */}
            <div className="px-4 py-2 border-t border-border/30 shrink-0 bg-card/30">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-muted-foreground/40 font-mono">
                  {modifiedMorphCount + modifiedBoneCount > 0
                    ? `${modifiedMorphCount + modifiedBoneCount} modified`
                    : 'ready'}
                </p>
                <p className="text-[10px] text-muted-foreground/30">
                  R G S 1-6 | Ctrl+Z/S
                </p>
              </div>
            </div>
          </>
        )}

        {/* Resize handle */}
        {sidebarOpen && (
          <div
            className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors z-30"
            onMouseDown={handleResizeStart}
          />
        )}
      </div>

      {/* ===== 3D Viewport ===== */}
      <div
        className="flex-1 relative min-w-0"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {/* Sidebar toggle (when closed) */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute top-3 left-3 z-10 p-2.5 rounded-xl glass border border-white/[0.06] text-white/50 hover:text-white/90 transition-all"
            title="패널 열기 (S)"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        {/* Viewer Toolbar */}
        <ViewerToolbar
          showGrid={showGrid}
          onToggleGrid={() => setShowGrid(!showGrid)}
          onResetCamera={() => viewerRef.current?.resetCamera()}
        />

        {/* 3D Canvas */}
        <WebGLCheck>
          <ThreeJSViewer
            ref={viewerRef}
            modelUrl={modelUrl}
            onModelLoaded={handleModelLoaded}
            showStats={false}
            showGrid={showGrid}
          />
        </WebGLCheck>

        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-primary/5 backdrop-blur-sm border-2 border-dashed border-primary/40 rounded-xl m-3 pointer-events-none">
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Upload className="w-8 h-8 text-primary/60" />
              </div>
              <p className="text-sm font-medium text-primary/80">
                VRM/GLB 파일을 여기에 드롭
              </p>
              <p className="text-xs text-primary/40">
                모델을 교체합니다
              </p>
            </div>
          </div>
        )}

        {/* Bottom info */}
        {!isDragging && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10">
            <div className="px-3 py-1.5 rounded-full glass border border-white/[0.06] text-[11px] text-white/30 flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400/60 animate-pulse" />
              VRM/GLB 드롭으로 모델 교체
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
