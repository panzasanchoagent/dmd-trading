#!/usr/bin/env node
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');
const distDir = path.join(projectRoot, '.next');
const args = process.argv.slice(2);
const command = args[0];
const nextArgs = args.slice(1);
const cwd = process.cwd();

function isOneDrivePath(targetPath) {
  return /[\\/]OneDrive(?:[\\/]|\s-\s)/i.test(targetPath);
}

function shouldCleanNextArtifacts() {
  if (process.env.TRIGGER_FORCE_NEXT_CLEAN === '1') return true;
  return process.platform === 'win32' && isOneDrivePath(cwd);
}

function cleanNextArtifacts() {
  if (!fs.existsSync(distDir)) return;
  fs.rmSync(distDir, { recursive: true, force: true });
}

if (!command) {
  console.error('[trigger] Missing next command (expected dev, build, or start).');
  process.exit(1);
}

if (shouldCleanNextArtifacts()) {
  console.warn('[trigger] Windows + OneDrive path detected. Removing frontend/.next before starting Next.js.');
  console.warn('[trigger] This avoids stale synced artifacts, but the durable fix is to keep the repo outside OneDrive or disable sync for this project.');
  cleanNextArtifacts();
}

const nextBin = require.resolve('next/dist/bin/next');
const child = spawn(process.execPath, [nextBin, command, ...nextArgs], {
  cwd: projectRoot,
  stdio: 'inherit',
  env: process.env,
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
