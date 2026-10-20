import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

test('Frontend structure and essential assets exist', () => {
  const indexHtml = join(process.cwd(), 'index.html');
  const packageJson = join(process.cwd(), 'package.json');
  const mainTsx = join(process.cwd(), 'src', 'main.tsx');
  const appTsx = join(process.cwd(), 'src', 'App.tsx');
  const translationsTs = join(process.cwd(), 'src', 'i18n', 'translations.ts');

  assert.ok(existsSync(indexHtml), 'index.html must exist');
  assert.ok(existsSync(packageJson), 'package.json must exist');
  assert.ok(existsSync(mainTsx), 'src/main.tsx must exist');
  assert.ok(existsSync(appTsx), 'src/App.tsx must exist');
  assert.ok(existsSync(translationsTs), 'translations.ts must exist');
});

test('Translations file contains both Hindi and English with all key routes', () => {
  const translationsContent = readFileSync(
    join(process.cwd(), 'src', 'i18n', 'translations.ts'),
    'utf-8'
  );

  assert.match(translationsContent, /hi:\s*\{/, 'Must define Hindi translations');
  assert.match(translationsContent, /en:\s*\{/, 'Must define English translations');
  assert.match(translationsContent, /schemes:/, 'Must contain schemes nav item');
  assert.match(translationsContent, /profile:/, 'Must contain profile nav item');
  assert.match(translationsContent, /documents:/, 'Must contain documents nav item');
  assert.match(translationsContent, /applications:/, 'Must contain applications nav item');
  assert.match(translationsContent, /followup:/, 'Must contain follow-up nav item');
  assert.match(translationsContent, /privacy:/, 'Must contain privacy nav item');
  assert.match(translationsContent, /endSession:/, 'Must contain endSession / wipe data item');
});
