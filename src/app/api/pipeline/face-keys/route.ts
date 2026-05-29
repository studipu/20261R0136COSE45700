import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile, mkdir, rm, cp } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { tmpdir } from 'os';
import { randomUUID } from 'crypto';

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = process.cwd();
const FACE_FEATURE_DIR = join(PROJECT_ROOT, 'face-feature');
const DEBUG_DIR = join(PROJECT_ROOT, 'debug', 'face-keys');

const TIMEOUT_MS = 3 * 60 * 1000; // 3 minutes

/** Resolve Python interpreter from env var or fallback to system python3 */
function getPython(): string {
  return process.env.PIPELINE_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
}

async function runPython(
  script: string,
  args: string[],
  cwd: string,
  label: string,
): Promise<string> {
  const python = getPython();
  console.log(`[FacePipeline] Running ${label} with ${python}...`);
  const { stdout, stderr } = await execFileAsync(python, [script, ...args], {
    cwd,
    timeout: TIMEOUT_MS,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });
  if (stderr) console.warn(`[FacePipeline] ${label} stderr:`, stderr);
  if (stdout) console.log(`[FacePipeline] ${label} stdout:`, stdout);
  return stdout;
}

export async function POST(request: NextRequest) {
  const workDir = join(tmpdir(), `face-pipeline-${randomUUID()}`);

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

    // Build CLI arguments
    const resultJson = join(workDir, 'result.json');
    const extractArgs = ['--image', imagePath, '--output', resultJson];

    // Optional: use rendered front view with depth maps for more accurate extraction
    const renderDir = formData.get('renderDir') as string | null;
    if (renderDir) {
      extractArgs.push('--render-dir', renderDir);
    }

    // Run face feature extraction pipeline
    await runPython(
      join(FACE_FEATURE_DIR, 'run_extract.py'),
      extractArgs,
      FACE_FEATURE_DIR,
      'face-feature run_extract',
    );

    // Read result JSON
    if (!existsSync(resultJson)) {
      return NextResponse.json(
        { status: 'error', error: 'Pipeline produced no output' },
        { status: 500 },
      );
    }

    const result = JSON.parse(await readFile(resultJson, 'utf-8'));

    // Save debug output (fire-and-forget — don't block response)
    const debugTs = new Date().toISOString().replace(/[:.]/g, '-');
    const debugOut = join(DEBUG_DIR, debugTs);
    cp(workDir, debugOut, { recursive: true })
      .then(() => console.log(`[FacePipeline] Debug saved: ${debugOut}`))
      .catch((e) => console.warn('[FacePipeline] Debug save failed:', e));

    return NextResponse.json(result);
  } catch (err) {
    console.error('[FacePipeline] Error:', err);
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json(
      { status: 'error', error: message },
      { status: 500 },
    );
  } finally {
    // Cleanup temp directory
    try {
      await rm(workDir, { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
  }
}
