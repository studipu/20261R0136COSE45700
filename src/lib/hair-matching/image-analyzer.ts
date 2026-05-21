/**
 * Extract dominant hair color from an uploaded image.
 *
 * Strategy:
 * 1. Draw image onto a canvas, downscaled to 128x128
 * 2. Sample the upper 40% (typical hair region in portrait/character images)
 * 3. Convert each pixel to HSL, filter out background pixels:
 *    - Very light (L > 0.92) — white/near-white background
 *    - Very low alpha — transparent background
 * 4. Cluster remaining pixels into buckets and find the dominant color
 * 5. Return hex color string
 */

import { hexToHsl, type HSL } from './color-distance';

export interface ImageHairColorResult {
  dominantColor: string; // hex
  hsl: HSL;
  sampleCount: number;
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
 * Extract dominant hair color from an image file.
 *
 * Samples the upper portion of the image where hair typically appears,
 * filters out background pixels, and computes the dominant color.
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

  // Sample the upper 40% of the image (hair region)
  const hairRegionHeight = Math.floor(SIZE * 0.4);
  const data = ctx.getImageData(0, 0, SIZE, hairRegionHeight).data;

  // Collect non-background pixels
  const pixels: { r: number; g: number; b: number }[] = [];

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const a = data[i + 3];

    // Skip transparent pixels
    if (a < 128) continue;

    const [, , l] = rgbToHsl(r, g, b);

    // Skip very light pixels (background)
    if (l > 0.92) continue;

    // Skip very dark pixels that are likely outlines/borders (optional)
    // Keep them as many hair colors are dark

    pixels.push({ r, g, b });
  }

  if (pixels.length === 0) {
    // Fallback: try the full image if upper region had no valid pixels
    const fullData = ctx.getImageData(0, 0, SIZE, SIZE).data;
    for (let i = 0; i < fullData.length; i += 4) {
      const r = fullData[i];
      const g = fullData[i + 1];
      const b = fullData[i + 2];
      const a = fullData[i + 3];
      if (a < 128) continue;
      const [, , l] = rgbToHsl(r, g, b);
      if (l > 0.92) continue;
      pixels.push({ r, g, b });
    }
  }

  if (pixels.length === 0) {
    console.log('[ImageAnalyzer] No valid pixels found in image');
    return null;
  }

  // Simple dominant color: use median-cut approximation
  // Bucket pixels into 8 hue bins, pick the largest non-achromatic bucket
  // If all achromatic, average everything

  const HUE_BINS = 8;
  const achromaticPixels: typeof pixels = [];
  const hueBuckets: (typeof pixels)[] = Array.from({ length: HUE_BINS }, () => []);

  for (const px of pixels) {
    const [h, s] = rgbToHsl(px.r, px.g, px.b);
    if (s < 0.08) {
      // Achromatic (gray/black/white)
      achromaticPixels.push(px);
    } else {
      const bin = Math.min(Math.floor((h / 360) * HUE_BINS), HUE_BINS - 1);
      hueBuckets[bin].push(px);
    }
  }

  // Find the largest chromatic bucket
  let bestBucket = achromaticPixels;
  let bestSize = 0;

  for (const bucket of hueBuckets) {
    if (bucket.length > bestSize) {
      bestSize = bucket.length;
      bestBucket = bucket;
    }
  }

  // If achromatic pixels dominate (>60%), use them instead
  if (achromaticPixels.length > pixels.length * 0.6) {
    bestBucket = achromaticPixels;
  }

  // Average the selected bucket
  const target = bestBucket.length > 0 ? bestBucket : pixels;
  let avgR = 0, avgG = 0, avgB = 0;
  for (const px of target) {
    avgR += px.r;
    avgG += px.g;
    avgB += px.b;
  }
  avgR = Math.round(avgR / target.length);
  avgG = Math.round(avgG / target.length);
  avgB = Math.round(avgB / target.length);

  const hex = '#' + [avgR, avgG, avgB].map((c) => c.toString(16).padStart(2, '0')).join('');
  const hsl = hexToHsl(hex);

  console.log(
    `[ImageAnalyzer] Extracted hair color: ${hex} ` +
    `(${target.length}/${pixels.length} pixels, hsl=[${hsl.map((v) => v.toFixed(2)).join(', ')}])`
  );

  return {
    dominantColor: hex,
    hsl,
    sampleCount: target.length,
  };
}
