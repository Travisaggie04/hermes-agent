import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'
import typesSource from './types.ts?raw'

describe('project-aware composer placeholder', () => {
  it('allows native chat to override the resting placeholder without changing disabled states', () => {
    expect(typesSource).toContain('placeholderOverride?: string')
    expect(source).toContain('placeholderOverride,')
    expect(source).toContain(': placeholderOverride || restingPlaceholder')
    expect(source).toContain('placeholderReconnecting')
    expect(source).toContain('placeholderStarting')
  })
})
