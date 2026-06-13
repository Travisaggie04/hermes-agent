const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

const MAIN_SOURCE = fs.readFileSync(path.join(__dirname, 'main.cjs'), 'utf8')

test('desktop main process enforces a single visible app instance', () => {
  assert.match(MAIN_SOURCE, /app\.requestSingleInstanceLock\(\)/)
  assert.match(MAIN_SOURCE, /app\.on\('second-instance'/)
  assert.match(MAIN_SOURCE, /mainWindow\.show\(\)/)
  assert.match(MAIN_SOURCE, /mainWindow\.focus\(\)/)
  assert.match(MAIN_SOURCE, /if \(hasSingleInstanceLock\) \{\s*app\.whenReady\(\)/)
})
