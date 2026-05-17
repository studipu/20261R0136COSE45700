/**
 * Browser test: upload 5.vrm as reference model and verify hair matching.
 * Uses Playwright to automate the browser interaction.
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VRM_PATH = path.resolve(__dirname, '../public/models/5.vrm');

(async () => {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Collect console logs
  const logs = [];
  page.on('console', (msg) => {
    const text = msg.text();
    logs.push(text);
    // Print hair-matching related logs in real time
    if (text.includes('[HairMatch]') || text.includes('[Materials]') || text.includes('[ReferenceUpload]')) {
      console.log('[BROWSER]', text);
    }
  });

  page.on('pageerror', (err) => {
    console.error('[PAGE ERROR]', err.message);
  });

  console.log('Navigating to /dev/viewer...');
  await page.goto('http://localhost:3000/dev/viewer', { waitUntil: 'networkidle', timeout: 30000 });

  // Wait for the master model to load (wait for sidebar tabs to appear)
  console.log('Waiting for master model to load...');
  await page.waitForSelector('button:has-text("스타일")', { timeout: 30000 });

  // Small delay for VRM to fully initialize
  await page.waitForTimeout(3000);

  // Click the Style tab
  console.log('Clicking Style tab...');
  await page.click('button:has-text("스타일")');
  await page.waitForTimeout(500);

  // Find the reference model upload area and upload the file
  console.log('Uploading 5.vrm as reference model...');

  // The hidden file input inside ReferenceModelUpload
  const fileInput = await page.locator('input[type="file"][accept=".vrm,.glb"]');

  if (await fileInput.count() === 0) {
    console.error('ERROR: File input not found! ReferenceModelUpload component may not be rendered.');

    // Debug: print page content
    const content = await page.textContent('body');
    console.log('Page body text (first 500 chars):', content?.slice(0, 500));
    await browser.close();
    process.exit(1);
  }

  await fileInput.setInputFiles(VRM_PATH);

  // Wait for processing (VRM load + material detection + matching)
  console.log('Waiting for hair matching to complete...');
  await page.waitForTimeout(10000);

  // Check for success indicator
  const successEl = await page.locator('text=적용됨').first();
  const hasSuccess = await successEl.isVisible().catch(() => false);

  const errorEl = await page.locator('text=감지하지 못했습니다').first();
  const hasError = await errorEl.isVisible().catch(() => false);

  console.log('\n=== RESULTS ===');

  if (hasSuccess) {
    const resultText = await successEl.textContent();
    console.log('SUCCESS:', resultText);
  } else if (hasError) {
    console.log('FAILED: Hair material not detected');
  } else {
    console.log('UNKNOWN: No success or error indicator found');
  }

  // Print all HairMatch logs
  console.log('\n=== All [HairMatch] Logs ===');
  const hairLogs = logs.filter((l) => l.includes('[HairMatch]') || l.includes('[ReferenceUpload]'));
  for (const log of hairLogs) {
    console.log('  ', log);
  }

  // Print any errors
  const errorLogs = logs.filter((l) => l.toLowerCase().includes('error') || l.toLowerCase().includes('fail'));
  if (errorLogs.length > 0) {
    console.log('\n=== Error Logs ===');
    for (const log of errorLogs) {
      console.log('  ', log);
    }
  }

  await browser.close();
  console.log('\nDone.');
})();
