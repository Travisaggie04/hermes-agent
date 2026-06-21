const assert = require('node:assert/strict')
const test = require('node:test')

const { buildPowerShellEnv, normalizeWindowsPowerShellModulePath, runBootstrap } = require('./bootstrap-runner.cjs')

test('runBootstrap bails immediately when the signal is already aborted', async () => {
  const controller = new AbortController()
  controller.abort()

  const events = []
  const result = await runBootstrap({
    installStamp: null,
    activeRoot: '/tmp/hermes-runner-test',
    sourceRepoRoot: null,
    hermesHome: '/tmp/hermes-runner-test',
    logRoot: '/tmp/hermes-runner-test',
    onEvent: ev => events.push(ev),
    abortSignal: controller.signal
  })

  // Cancelled before any install script is spawned.
  assert.deepEqual(result, { ok: false, cancelled: true })
  assert.ok(
    events.some(ev => ev.type === 'failed' && /cancelled/i.test(ev.error)),
    'should emit a cancelled failure event'
  )
})

test('buildPowerShellEnv limits PSModulePath to Windows PowerShell modules on Windows', () => {
  const baseEnv = {
    HERMES_HOME: 'C:\\old-hermes',
    Path: 'C:\\Windows\\System32',
    ProgramFiles: 'C:\\Program Files',
    PSMODULEPATH: 'C:\\Program Files\\PowerShell\\Modules',
    PSModulePath: [
      'C:\\Users\\Travis\\Documents\\PowerShell\\Modules',
      'C:\\Program Files\\PowerShell\\Modules',
      'C:\\Program Files\\WindowsPowerShell\\Modules',
      'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules',
      'C:\\custom\\WindowsPowerShell\\Modules'
    ].join(';'),
    SystemRoot: 'C:\\Windows',
    USERPROFILE: 'C:\\Users\\Travis'
  }

  const env = buildPowerShellEnv({
    baseEnv,
    hermesHome: 'C:\\fresh-hermes',
    platform: 'win32'
  })

  assert.equal(env.HERMES_HOME, 'C:\\fresh-hermes')
  assert.equal(Object.keys(env).filter(key => key.toLowerCase() === 'psmodulepath').length, 1)
  assert.equal(
    env.PSModulePath,
    [
      'C:\\Users\\Travis\\Documents\\WindowsPowerShell\\Modules',
      'C:\\Program Files\\WindowsPowerShell\\Modules',
      'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules',
      'C:\\custom\\WindowsPowerShell\\Modules'
    ].join(';')
  )
})

test('normalizeWindowsPowerShellModulePath falls back to core module paths', () => {
  assert.equal(
    normalizeWindowsPowerShellModulePath({
      ProgramFiles: 'D:\\Program Files',
      PSModulePath: 'C:\\Program Files\\PowerShell\\Modules',
      SystemRoot: 'D:\\Windows',
      USERPROFILE: 'D:\\Users\\Jenny'
    }),
    [
      'D:\\Users\\Jenny\\Documents\\WindowsPowerShell\\Modules',
      'D:\\Program Files\\WindowsPowerShell\\Modules',
      'D:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules'
    ].join(';')
  )
})
