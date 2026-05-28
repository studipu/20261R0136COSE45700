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
const FACE_PIPELINE_DIR = join(PROJECT_ROOT, 'src', 'pipeline', 'face');
const DEBUG_DIR = join(PROJECT_ROOT, 'debug', 'generate-3d');

// VARCO takes 2-5 min + render 30s + extraction 30s
const TIMEOUT_MS = 7 * 60 * 1000; // 7 minutes

/** Resolve Python interpreter from env var or fallback to system python3 */
function getPython(): string {
  return process.env.PIPELINE_PYTHON || 'python3';
}

async function runPython(
  script: string,
  args: string[],
  cwd: string,
  label: string,
): Promise<string> {
  const python = getPython();
  console.log(`[Generate3D] Running ${label} with ${python}...`);
  const { stdout, stderr } = await execFileAsync(python, [script, ...args], {
    cwd,
    timeout: TIMEOUT_MS,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });
  if (stderr) console.warn(`[Generate3D] ${label} stderr:`, stderr);
  if (stdout) console.log(`[Generate3D] ${label} stdout:`, stdout);
  return stdout;
}

export async function POST(request: NextRequest) {
  const workDir = join(tmpdir(), `generate-3d-${randomUUID()}`);

  try {
    // Parse multipart form data
    const formData = await request.formData();
    const imageFile = formData.get('image') as File | null;
    const provider = (formData.get('provider') as string) || process.env.VARCO_PROVIDER || 'meshy';
    const apiKey = (formData.get('apiKey') as string) || process.env.VARCO_API_KEY || '';
    const skip3d = formData.get('skip3d') === 'true';
    const existingGlb = formData.get('existingGlb') as string | null;

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
    const pipelineArgs = [
      '--image', imagePath,
      '--output-dir', workDir,
      '--provider', provider,
    ];

    if (apiKey) {
      pipelineArgs.push('--api-key', apiKey);
    }
    if (skip3d) {
      pipelineArgs.push('--skip-3d');
    }
    if (existingGlb) {
      pipelineArgs.push('--existing-glb', existingGlb);
    }

    // Run full pipeline
    await runPython(
      join(FACE_PIPELINE_DIR, 'run_pipeline.py'),
      pipelineArgs,
      FACE_PIPELINE_DIR,
      'run_pipeline',
    );

    // Read result JSON
    const resultJson = join(workDir, 'pipeline_result.json');
    if (!existsSync(resultJson)) {
      return NextResponse.json(
        { status: 'error', error: 'Pipeline produced no output' },
        { status: 500 },
      );
    }

    const result = JSON.parse(await readFile(resultJson, 'utf-8'));

    // Save debug output
    try {
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const debugOut = join(DEBUG_DIR, ts);
      await cp(workDir, debugOut, { recursive: true });
      console.log(`[Generate3D] Debug saved: ${debugOut}`);
    } catch (e) {
      console.warn('[Generate3D] Debug save failed:', e);
    }

    return NextResponse.json(result);
  } catch (err) {
    console.error('[Generate3D] Error:', err);
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
