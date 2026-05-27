import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile, mkdir, rm } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { tmpdir } from 'os';
import { randomUUID } from 'crypto';

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = process.cwd();
const PIPELINE_DIR = join(PROJECT_ROOT, 'src', 'pipeline');
const FACE_PIPELINE_DIR = join(PIPELINE_DIR, 'face');
const KANOSAWA_DIR = join(PIPELINE_DIR, 'kanosawa');
const TEXTURES_DIR = join(PIPELINE_DIR, 'assets', 'textures');
const THUMBNAILS_DIR = join(PROJECT_ROOT, 'public', 'thumbnails');

const TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

/** Resolve Python interpreter from env var or fallback to system python3 */
function getPython(): string {
  return process.env.PIPELINE_PYTHON || 'python3';
}

/** Pipeline output filename → VRM material slot regex mapping */
const TEXTURE_SLOT_MAP: Record<string, RegExp> = {
  'BaseTexture_Generate_Face.png': /face|skin/i,
  'BaseTexture_Generate_Eyebrow.png': /eyebrow|brow/i,
  'BaseTexture_Generate_Eyeline.png': /eyeline|eyelash|eyelid/i,
  'BaseTexture_Generate_Pupil.png': /eye|iris|pupil/i,
  'BaseTexture_Static_EyeWhite.png': /sclera|eyewhite/i,
  'BaseTexture_Static_EyeHighlight.png': /highlight/i,
  'BaseTexture_Static_MouthInside.png': /mouth/i,
};

async function runPython(
  script: string,
  args: string[],
  cwd: string,
  label: string,
): Promise<string> {
  const python = getPython();
  console.log(`[TexturePipeline] Running ${label} with ${python}...`);
  const { stdout, stderr } = await execFileAsync(python, [script, ...args], {
    cwd,
    timeout: TIMEOUT_MS,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });
  if (stderr) console.warn(`[TexturePipeline] ${label} stderr:`, stderr);
  if (stdout) console.log(`[TexturePipeline] ${label} stdout:`, stdout);
  return stdout;
}

export async function POST(request: NextRequest) {
  const workDir = join(tmpdir(), `texture-pipeline-${randomUUID()}`);

  try {
    // Parse multipart form data
    const formData = await request.formData();
    const imageFile = formData.get('image') as File | null;

    if (!imageFile) {
      return NextResponse.json({ error: 'No image file provided' }, { status: 400 });
    }

    // Create work directory
    await mkdir(workDir, { recursive: true });

    // Save uploaded image
    const imageBuffer = Buffer.from(await imageFile.arrayBuffer());
    const imagePath = join(workDir, 'input.png');
    await writeFile(imagePath, imageBuffer);

    // Step 1: Extract landmarks
    const landmarkOutput = join(workDir, 'landmarks_annotated.png');
    const landmarksJson = join(workDir, 'landmarks.json');
    await runPython(
      join(KANOSAWA_DIR, 'extract_landmarks.py'),
      [imagePath, landmarkOutput, '--landmarks_json', landmarksJson],
      KANOSAWA_DIR,
      'extract_landmarks',
    );

    // Step 2: Extract features (Gemini API)
    const featuresJson = join(workDir, 'features.json');
    await runPython(
      join(PIPELINE_DIR, 'extract_features.py'),
      ['--image', imagePath, '--output', featuresJson],
      PIPELINE_DIR,
      'extract_features',
    );

    // Step 3, 4 & 5: Adjust textures + analyze hairstyle + face-keys (in parallel)
    const outputDir = join(workDir, 'output');
    const hairMatchJson = join(workDir, 'hair_match.json');
    const faceKeysJson = join(workDir, 'face_keys.json');

    const [, hairMatchResult, faceKeysResult] = await Promise.allSettled([
      runPython(
        join(PIPELINE_DIR, 'adjust_texture.py'),
        ['--features', featuresJson, '--input_dir', TEXTURES_DIR, '--output_dir', outputDir],
        PIPELINE_DIR,
        'adjust_texture',
      ),
      runPython(
        join(PIPELINE_DIR, 'analyze_hairstyle.py'),
        ['--image', imagePath, '--landmarks', landmarksJson, '--features', featuresJson, '--output', hairMatchJson],
        PIPELINE_DIR,
        'analyze_hairstyle',
      ),
      runPython(
        join(FACE_PIPELINE_DIR, 'run_extract.py'),
        ['--image', imagePath, '--output', faceKeysJson, '--features', featuresJson, '--landmarks', landmarksJson],
        FACE_PIPELINE_DIR,
        'run_extract (face-keys)',
      ),
    ]);

    // Read generated textures and encode as base64
    const textures: Record<string, string> = {};

    for (const [filename, slotRegex] of Object.entries(TEXTURE_SLOT_MAP)) {
      const texturePath = join(outputDir, filename);
      if (!existsSync(texturePath)) continue;

      const data = await readFile(texturePath);
      const base64 = data.toString('base64');
      const dataUrl = `data:image/png;base64,${base64}`;

      // Use the filename (without extension) as key, store the regex source for frontend matching
      const slotKey = filename.replace('.png', '');
      textures[slotKey] = dataUrl;
    }

    // Read features, landmarks, hair match, and face-keys for frontend use
    let features: unknown = null;
    let landmarks: unknown = null;
    let hairMatch: unknown = null;
    let faceKeys: unknown = null;
    try {
      if (existsSync(featuresJson)) {
        features = JSON.parse(await readFile(featuresJson, 'utf-8'));
      }
      if (existsSync(landmarksJson)) {
        landmarks = JSON.parse(await readFile(landmarksJson, 'utf-8'));
      }
      if (hairMatchResult?.status === 'fulfilled' && existsSync(hairMatchJson)) {
        hairMatch = JSON.parse(await readFile(hairMatchJson, 'utf-8'));
        console.log('[TexturePipeline] Hair match result:', JSON.stringify(hairMatch));
      } else if (hairMatchResult?.status === 'rejected') {
        console.warn('[TexturePipeline] Hair matching failed:', hairMatchResult.reason);
      }
      if (faceKeysResult?.status === 'fulfilled' && existsSync(faceKeysJson)) {
        faceKeys = JSON.parse(await readFile(faceKeysJson, 'utf-8'));
        console.log('[TexturePipeline] Face keys extracted');
      } else if (faceKeysResult?.status === 'rejected') {
        console.warn('[TexturePipeline] Face keys extraction failed:', faceKeysResult.reason);
      }
    } catch {
      // non-critical
    }

    return NextResponse.json({ textures, features, landmarks, hairMatch, faceKeys });
  } catch (err) {
    console.error('[TexturePipeline] Error:', err);
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  } finally {
    // Cleanup temp directory
    try {
      await rm(workDir, { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
  }
}
