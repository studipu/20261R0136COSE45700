/**
 * HSL-based perceptual color distance for hair matching.
 */

export type HSL = [h: number, s: number, l: number];

/**
 * Convert hex color string to HSL [0-360, 0-1, 0-1].
 */
export function hexToHsl(hex: string): HSL {
  const raw = hex.replace('#', '');
  const r = parseInt(raw.slice(0, 2), 16) / 255;
  const g = parseInt(raw.slice(2, 4), 16) / 255;
  const b = parseInt(raw.slice(4, 6), 16) / 255;

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

  return [h * 360, s, l];
}

/**
 * Compute perceptual color similarity in HSL space (0~1, 1 = identical).
 *
 * Weights: H=0.35, S=0.25, L=0.40
 * Hue uses circular distance with saturation attenuation (achromatic colors ignore hue).
 */
export function colorSimilarity(hsl1: HSL, hsl2: HSL): number {
  const [h1, s1, l1] = hsl1;
  const [h2, s2, l2] = hsl2;

  // Circular hue distance (0~180 → normalized to 0~1)
  const rawHueDiff = Math.abs(h1 - h2);
  const hueDiff = Math.min(rawHueDiff, 360 - rawHueDiff) / 180;

  // Saturation attenuation: when both colors are near-achromatic, hue doesn't matter
  const avgSat = (s1 + s2) / 2;
  const hueWeight = 0.35 * avgSat; // attenuate hue by average saturation

  const satDiff = Math.abs(s1 - s2);
  const lightDiff = Math.abs(l1 - l2);

  // Redistribute hue weight to lightness when saturation is low
  const redistributedLightWeight = 0.40 + 0.35 * (1 - avgSat);
  const satWeight = 0.25;

  const distance = hueWeight * hueDiff + satWeight * satDiff + redistributedLightWeight * lightDiff;

  // Clamp to [0, 1]
  return Math.max(0, 1 - distance);
}
