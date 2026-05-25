/**
 * Color distance utilities for hair matching.
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
 * Weights: H=0.45, S=0.15, L=0.40
 * Hue uses circular distance with saturation attenuation (achromatic colors ignore hue).
 * Hue is weighted more heavily than saturation to avoid preferring a wrong hue
 * (e.g. auburn) over a correct hue (e.g. warm brown) just because saturation is closer.
 */
export function colorSimilarity(hsl1: HSL, hsl2: HSL): number {
  const [h1, s1, l1] = hsl1;
  const [h2, s2, l2] = hsl2;

  // Circular hue distance (0~180 → normalized to 0~1)
  const rawHueDiff = Math.abs(h1 - h2);
  const hueDiff = Math.min(rawHueDiff, 360 - rawHueDiff) / 180;

  // Saturation attenuation: when both colors are near-achromatic, hue doesn't matter
  const avgSat = (s1 + s2) / 2;
  const hueWeight = 0.45 * avgSat; // attenuate hue by average saturation

  const satDiff = Math.abs(s1 - s2);
  const lightDiff = Math.abs(l1 - l2);

  // Redistribute hue weight to lightness when saturation is low
  const redistributedLightWeight = 0.40 + 0.45 * (1 - avgSat);
  const satWeight = 0.15;

  const distance = hueWeight * hueDiff + satWeight * satDiff + redistributedLightWeight * lightDiff;

  // Clamp to [0, 1]
  return Math.max(0, 1 - distance);
}

/**
 * Parse hex color to RGB [0-255].
 */
function hexToRgb(hex: string): [number, number, number] {
  const raw = hex.replace('#', '');
  return [
    parseInt(raw.slice(0, 2), 16),
    parseInt(raw.slice(2, 4), 16),
    parseInt(raw.slice(4, 6), 16),
  ];
}

// ---- CIE Lab Color Space ----

export type Lab = [L: number, a: number, b: number];

/**
 * Convert sRGB [0-255] to CIE XYZ (D65 illuminant).
 */
function rgbToXyz(r: number, g: number, b: number): [number, number, number] {
  // Linearize sRGB
  let rn = r / 255;
  let gn = g / 255;
  let bn = b / 255;

  rn = rn > 0.04045 ? Math.pow((rn + 0.055) / 1.055, 2.4) : rn / 12.92;
  gn = gn > 0.04045 ? Math.pow((gn + 0.055) / 1.055, 2.4) : gn / 12.92;
  bn = bn > 0.04045 ? Math.pow((bn + 0.055) / 1.055, 2.4) : bn / 12.92;

  // sRGB → XYZ (D65)
  const x = rn * 0.4124564 + gn * 0.3575761 + bn * 0.1804375;
  const y = rn * 0.2126729 + gn * 0.7151522 + bn * 0.0721750;
  const z = rn * 0.0193339 + gn * 0.1191920 + bn * 0.9503041;

  return [x, y, z];
}

/**
 * Convert CIE XYZ to CIE Lab (D65 illuminant).
 */
function xyzToLab(x: number, y: number, z: number): Lab {
  // D65 reference white
  const xn = 0.95047;
  const yn = 1.00000;
  const zn = 1.08883;

  let fx = x / xn;
  let fy = y / yn;
  let fz = z / zn;

  const epsilon = 0.008856;
  const kappa = 903.3;

  fx = fx > epsilon ? Math.cbrt(fx) : (kappa * fx + 16) / 116;
  fy = fy > epsilon ? Math.cbrt(fy) : (kappa * fy + 16) / 116;
  fz = fz > epsilon ? Math.cbrt(fz) : (kappa * fz + 16) / 116;

  const L = 116 * fy - 16;
  const a = 500 * (fx - fy);
  const b = 200 * (fy - fz);

  return [L, a, b];
}

/**
 * Convert hex color to CIE Lab.
 */
export function hexToLab(hex: string): Lab {
  const [r, g, b] = hexToRgb(hex);
  const [x, y, z] = rgbToXyz(r, g, b);
  return xyzToLab(x, y, z);
}

/**
 * CIE Lab Delta E (CIE76) color distance.
 * Returns Euclidean distance in Lab space — perceptually uniform by design.
 * Typical range: 0 (identical) to ~100+ (black vs white ≈ 100).
 */
function deltaE(lab1: Lab, lab2: Lab): number {
  const dL = lab1[0] - lab2[0];
  const da = lab1[1] - lab2[1];
  const db = lab1[2] - lab2[2];
  return Math.sqrt(dL * dL + da * da + db * db);
}

/**
 * CIE Lab-based color similarity (0~1, 1 = identical).
 *
 * Uses CIE76 Delta E in CIELAB color space, which was designed to be
 * perceptually uniform — equal numeric distances correspond to equal
 * perceived color differences regardless of hue/saturation/lightness.
 * No arbitrary channel weighting needed.
 *
 * Max Delta E ≈ 100 (black vs white). Normalized to 0~1 similarity.
 */
export function colorSimilarityLab(hex1: string, hex2: string): number {
  const lab1 = hexToLab(hex1);
  const lab2 = hexToLab(hex2);
  const de = deltaE(lab1, lab2);
  // Max Delta E ≈ 100 for most practical color pairs
  return Math.max(0, 1 - de / 100);
}
