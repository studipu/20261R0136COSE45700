/**
 * Extract dominant hair color from an uploaded image.
 *
 * Strategy:
 * 1. Draw image onto a canvas, downscaled to 128x128
 * 2. Detect background color by sampling the 4 corners
 * 3. Sample the upper-center region (hair area in portrait images)
 * 4. Filter out background-similar and skin-like pixels
 * 5. Cluster remaining pixels by hue and find the dominant hair color
 */

import { hexToHsl, type HSL } from './color-distance';

export interface ImageHairColorResult {
  dominantColor: string; // hex
  hsl: HSL;
  sampleCount: number;
}

interface Pixel {
  r: number;
  g: number;
  b: number;
}

/**
 * Convert RGB [0-255] to HSL [H: 0-360, S: 0-1, L: 0-1]
 */
function rgbToHsl(r: number, g: number, b: number): HSL {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;

  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;

  if (max === min) return [0, 0, l];

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h = 0;
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;

  return [h * 360, s, l];
}

/**
 * Euclidean distance between two RGB pixels (0-255 range).
 */
function rgbDistance(a: Pixel, b: Pixel): number {
  const dr = a.r - b.r;
  const dg = a.g - b.g;
  const db = a.b - b.b;
  return Math.sqrt(dr * dr + dg * dg + db * db);
}

/**
 * Load an image File/Blob into an HTMLImageElement.
 */
function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };
    img.src = url;
  });
}

/**
 * Sample a small region of the canvas and return average color.
 */
function sampleRegion(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
): Pixel {
  const data = ctx.getImageData(x, y, w, h).data;
  let r = 0, g = 0, b = 0, count = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue;
    r += data[i];
    g += data[i + 1];
    b += data[i + 2];
    count++;
  }
  if (count === 0) return { r: 128, g: 128, b: 128 };
  return {
    r: Math.round(r / count),
    g: Math.round(g / count),
    b: Math.round(b / count),
  };
}

/**
 * Detect background color by sampling the 4 corners of the image.
 * Returns the average of corner samples.
 */
function detectBackground(ctx: CanvasRenderingContext2D, size: number): Pixel {
  const patch = 8; // 8x8 corner patches
  const corners = [
    sampleRegion(ctx, 0, 0, patch, patch),                         // top-left
    sampleRegion(ctx, size - patch, 0, patch, patch),               // top-right
    sampleRegion(ctx, 0, size - patch, patch, patch),               // bottom-left
    sampleRegion(ctx, size - patch, size - patch, patch, patch),    // bottom-right
  ];

  // Average the corners
  let r = 0, g = 0, b = 0;
  for (const c of corners) {
    r += c.r;
    g += c.g;
    b += c.b;
  }

  const bg = {
    r: Math.round(r / corners.length),
    g: Math.round(g / corners.length),
    b: Math.round(b / corners.length),
  };

  console.log(`[ImageAnalyzer] Detected background: rgb(${bg.r},${bg.g},${bg.b})`);
  return bg;
}

/**
 * Check if a pixel is skin-like.
 * Uses tight ranges to avoid false-positives on auburn (H:0-20°) and golden (H:30-45°) hair.
 * Real skin: narrow hue (10-35°), moderate saturation, high lightness, and r > g > b ordering.
 */
function isSkinLike(r: number, g: number, b: number): boolean {
  // Structural check: skin always has r > g > b
  if (!(r > g && g > b)) return false;

  const [h, s, l] = rgbToHsl(r, g, b);
  // Tight ranges: hue 10-35°, saturation 0.2-0.55, lightness 0.6-0.85
  return h >= 10 && h <= 35 && s >= 0.2 && s <= 0.55 && l >= 0.6 && l <= 0.85;
}

/**
 * Extract dominant hair color from an image file.
 */
export async function extractHairColorFromImage(
  file: File,
): Promise<ImageHairColorResult | null> {
  const img = await loadImage(file);

  const SIZE = 128;
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  ctx.drawImage(img, 0, 0, SIZE, SIZE);

  // Step 1: Detect background color from corners
  const bgColor = detectBackground(ctx, SIZE);
  const BG_THRESHOLD = 45; // RGB distance threshold for background similarity

  // Step 2: Sample the upper-center region (avoid edges where background is)
  // Horizontal: center 70% (skip 15% on each side)
  // Vertical: top 45%
  const marginX = Math.floor(SIZE * 0.15);
  const regionW = SIZE - marginX * 2;
  const regionH = Math.floor(SIZE * 0.45);
  const data = ctx.getImageData(marginX, 0, regionW, regionH).data;

  // Step 3: Collect pixels, filtering background and skin
  const pixels: Pixel[] = [];

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const a = data[i + 3];

    // Skip transparent
    if (a < 128) continue;

    const px: Pixel = { r, g, b };

    // Skip background-similar pixels
    if (rgbDistance(px, bgColor) < BG_THRESHOLD) continue;

    const [, , l] = rgbToHsl(r, g, b);

    // Skip very light (white background remnants)
    if (l > 0.92) continue;

    // Skip skin-like pixels (face area that may overlap with hair region)
    if (isSkinLike(r, g, b)) continue;

    pixels.push(px);
  }

  // Fallback: if no valid pixels in upper-center, try full upper region
  if (pixels.length < 20) {
    const fullData = ctx.getImageData(0, 0, SIZE, Math.floor(SIZE * 0.5)).data;
    for (let i = 0; i < fullData.length; i += 4) {
      const r = fullData[i];
      const g = fullData[i + 1];
      const b = fullData[i + 2];
      const a = fullData[i + 3];
      if (a < 128) continue;
      const px: Pixel = { r, g, b };
      if (rgbDistance(px, bgColor) < BG_THRESHOLD) continue;
      const [, , l] = rgbToHsl(r, g, b);
      if (l > 0.92) continue;
      if (isSkinLike(r, g, b)) continue;
      pixels.push(px);
    }
  }

  if (pixels.length === 0) {
    console.log('[ImageAnalyzer] No valid pixels found after filtering');
    return null;
  }

  // Step 4: Cluster by hue and find dominant color
  // 24 bins = 15° per bin — separates red (0-15°), brown (15-30°), golden (30-45°) etc.
  const HUE_BINS = 24;
  const achromaticPixels: Pixel[] = [];
  const hueBuckets: Pixel[][] = Array.from({ length: HUE_BINS }, () => []);

  for (const px of pixels) {
    const [h, s] = rgbToHsl(px.r, px.g, px.b);
    if (s < 0.08) {
      achromaticPixels.push(px);
    } else {
      const bin = Math.min(Math.floor((h / 360) * HUE_BINS), HUE_BINS - 1);
      hueBuckets[bin].push(px);
    }
  }

  // Log bin distribution for debugging
  const binLog = hueBuckets
    .map((b, i) => b.length > 0 ? `bin${i}(${i * 15}-${(i + 1) * 15}°):${b.length}` : null)
    .filter(Boolean)
    .join(', ');
  console.log(`[ImageAnalyzer] Hue bins: ${binLog}, achromatic: ${achromaticPixels.length}`);

  // Find the largest chromatic bucket
  let bestBucket: Pixel[] = [];
  let bestSize = 0;
  let bestBinIdx = -1;
  for (let i = 0; i < hueBuckets.length; i++) {
    if (hueBuckets[i].length > bestSize) {
      bestSize = hueBuckets[i].length;
      bestBucket = hueBuckets[i];
      bestBinIdx = i;
    }
  }

  // If achromatic pixels dominate (>60%), use them (black/gray hair)
  if (achromaticPixels.length > pixels.length * 0.6) {
    bestBucket = achromaticPixels;
    bestBinIdx = -1;
  }

  // If no chromatic bucket found, fall back to achromatic
  if (bestBucket.length === 0) {
    bestBucket = achromaticPixels.length > 0 ? achromaticPixels : pixels;
  }

  console.log(
    `[ImageAnalyzer] Selected bin: ${bestBinIdx >= 0 ? `${bestBinIdx} (${bestBinIdx * 15}-${(bestBinIdx + 1) * 15}°)` : 'achromatic'} ` +
    `with ${bestBucket.length} pixels`
  );

  // Use median color (more robust than mean — resistant to outlier dilution)
  const sortedR = bestBucket.map((px) => px.r).sort((a, b) => a - b);
  const sortedG = bestBucket.map((px) => px.g).sort((a, b) => a - b);
  const sortedB = bestBucket.map((px) => px.b).sort((a, b) => a - b);
  const mid = Math.floor(bestBucket.length / 2);
  const medR = sortedR[mid];
  const medG = sortedG[mid];
  const medB = sortedB[mid];

  const hex = '#' + [medR, medG, medB].map((c) => c.toString(16).padStart(2, '0')).join('');
  const hsl = hexToHsl(hex);

  console.log(
    `[ImageAnalyzer] Extracted hair color: ${hex} ` +
    `(${bestBucket.length}/${pixels.length} valid pixels, ` +
    `bg filtered with threshold=${BG_THRESHOLD}, ` +
    `hsl=[${hsl.map((v) => v.toFixed(2)).join(', ')}])`
  );

  return {
    dominantColor: hex,
    hsl,
    sampleCount: bestBucket.length,
  };
}
