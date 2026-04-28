'use client';

import { useCallback, useRef } from 'react';

export function useCanvasScreenshot() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const findCanvas = useCallback(() => {
    if (canvasRef.current) return canvasRef.current;
    // Find the R3F canvas in the DOM
    const canvas = document.querySelector('canvas');
    if (canvas) canvasRef.current = canvas;
    return canvas;
  }, []);

  const capture = useCallback(async (size = 128): Promise<string | undefined> => {
    const canvas = findCanvas();
    if (!canvas) return undefined;

    try {
      // Create a temporary canvas for resizing
      const tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = size;
      tmpCanvas.height = size;
      const ctx = tmpCanvas.getContext('2d');
      if (!ctx) return undefined;

      // Draw the 3D canvas onto the temp canvas (scaled)
      ctx.drawImage(canvas, 0, 0, size, size);
      return tmpCanvas.toDataURL('image/png');
    } catch {
      return undefined;
    }
  }, [findCanvas]);

  return { capture };
}
