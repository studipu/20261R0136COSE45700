'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  presets?: readonly string[];
  label?: string;
}

function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return [h, s, l];
}

function hslToHex(h: number, s: number, l: number): string {
  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  let r: number, g: number, b: number;
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  const toHex = (v: number) => Math.round(v * 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export function ColorPicker({ color, onChange, presets, label }: ColorPickerProps) {
  const [hsl, setHsl] = useState(() => hexToHsl(color));
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const satLightRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // Sync when external color changes
  useEffect(() => {
    setHsl(hexToHsl(color));
  }, [color]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [isOpen]);

  const updateColor = useCallback(
    (h: number, s: number, l: number) => {
      setHsl([h, s, l]);
      onChange(hslToHex(h, s, l));
    },
    [onChange]
  );

  const handleHueChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const h = parseFloat(e.target.value);
      updateColor(h, hsl[1], hsl[2]);
    },
    [hsl, updateColor]
  );

  const handleSatLightPointer = useCallback(
    (clientX: number, clientY: number) => {
      const el = satLightRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const s = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const l = Math.max(0, Math.min(1, 1 - (clientY - rect.top) / rect.height));
      updateColor(hsl[0], s, l);
    },
    [hsl, updateColor]
  );

  const handleSatLightMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isDragging.current = true;
      handleSatLightPointer(e.clientX, e.clientY);
      const handleMove = (ev: MouseEvent) => {
        if (isDragging.current) handleSatLightPointer(ev.clientX, ev.clientY);
      };
      const handleUp = () => {
        isDragging.current = false;
        document.removeEventListener('mousemove', handleMove);
        document.removeEventListener('mouseup', handleUp);
      };
      document.addEventListener('mousemove', handleMove);
      document.addEventListener('mouseup', handleUp);
    },
    [handleSatLightPointer]
  );

  return (
    <div ref={containerRef} className="relative">
      {label && (
        <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-md border border-border hover:border-primary/50 transition-colors w-full"
      >
        <div
          className="w-5 h-5 rounded border border-border/50 shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="text-xs font-mono text-muted-foreground">{color.toUpperCase()}</span>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 p-3 rounded-lg border border-border bg-card shadow-xl w-56">
          {/* Saturation/Lightness area */}
          <div
            ref={satLightRef}
            className="w-full h-32 rounded cursor-crosshair relative mb-2"
            style={{
              background: `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, hsl(${hsl[0] * 360}, 100%, 50%))`,
            }}
            onMouseDown={handleSatLightMouseDown}
          >
            <div
              className="absolute w-3 h-3 rounded-full border-2 border-white shadow-md -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              style={{
                left: `${hsl[1] * 100}%`,
                top: `${(1 - hsl[2]) * 100}%`,
                backgroundColor: color,
              }}
            />
          </div>

          {/* Hue slider */}
          <input
            type="range"
            min="0"
            max="1"
            step="0.005"
            value={hsl[0]}
            onChange={handleHueChange}
            className="w-full h-3 rounded-full appearance-none cursor-pointer mb-2"
            style={{
              background: 'linear-gradient(to right, #f00 0%, #ff0 17%, #0f0 33%, #0ff 50%, #00f 67%, #f0f 83%, #f00 100%)',
            }}
          />

          {/* Hex input */}
          <input
            type="text"
            value={color.toUpperCase()}
            onChange={(e) => {
              const v = e.target.value;
              if (/^#[0-9a-fA-F]{6}$/.test(v)) {
                onChange(v);
              }
            }}
            className="w-full px-2 py-1 text-xs font-mono bg-background border border-border rounded text-foreground mb-2"
            maxLength={7}
          />

          {/* Presets */}
          {presets && presets.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {presets.map((preset) => (
                <button
                  key={preset}
                  onClick={() => onChange(preset)}
                  className={`w-5 h-5 rounded border transition-all ${
                    color.toLowerCase() === preset.toLowerCase()
                      ? 'border-primary ring-1 ring-primary scale-110'
                      : 'border-border/50 hover:scale-110'
                  }`}
                  style={{ backgroundColor: preset }}
                  title={preset}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
