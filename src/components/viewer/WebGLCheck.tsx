'use client';

import { useEffect, useState } from 'react';
import { isWebGL2Supported } from '@/lib/webgl/detect';
import { Box, AlertTriangle } from 'lucide-react';

interface WebGLCheckProps {
  children: React.ReactNode;
}

export function WebGLCheck({ children }: WebGLCheckProps) {
  const [supported, setSupported] = useState<boolean | null>(null);

  useEffect(() => {
    setSupported(isWebGL2Supported());
  }, []);

  if (supported === null) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center animate-pulse">
            <Box className="w-7 h-7 text-primary/50" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground/60">3D 엔진 초기화 중</p>
            <p className="text-[11px] text-muted-foreground/40 mt-1">WebGL 지원 여부 확인 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!supported) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 max-w-xs text-center">
          <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="w-7 h-7 text-destructive/60" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">
              WebGL 2.0 미지원 브라우저
            </p>
            <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
              3D 뷰어를 사용하려면 Chrome, Firefox, Safari, Edge 최신 버전이 필요합니다.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
