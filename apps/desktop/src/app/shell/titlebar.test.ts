import { describe, expect, it } from 'vitest'

import {
  TITLEBAR_CONTROL_OFFSET_X,
  TITLEBAR_EDGE_INSET,
  TITLEBAR_FALLBACK_WINDOW_BUTTON_X,
  titlebarControlsPosition,
  titlebarHeaderBaseClass
} from './titlebar'

describe('titlebarControlsPosition', () => {
  it('offsets controls from visible traffic lights', () => {
    expect(titlebarControlsPosition({ x: 24, y: 10 }).left).toBe(24 + TITLEBAR_CONTROL_OFFSET_X)
  })

  it('pins to the edge when macOS fullscreen hides traffic lights', () => {
    expect(titlebarControlsPosition({ x: 24, y: 10 }, true).left).toBe(TITLEBAR_EDGE_INSET)
  })

  it('pins to the edge on Windows/Linux where native controls render on the right', () => {
    expect(titlebarControlsPosition(null).left).toBe(TITLEBAR_EDGE_INSET)
  })

  it('uses the macOS fallback while the initial window state is unknown', () => {
    expect(titlebarControlsPosition(undefined).left).toBe(TITLEBAR_FALLBACK_WINDOW_BUTTON_X + TITLEBAR_CONTROL_OFFSET_X)
  })

  it('reserves left title space when the left pane track is closed', () => {
    expect(titlebarHeaderBaseClass).toContain('var(--titlebar-left-safe-inset')
    expect(titlebarHeaderBaseClass).toContain('var(--titlebar-left-pane-width')
  })

  it('reserves the fixed right titlebar controls and clips crowded header content', () => {
    expect(titlebarHeaderBaseClass).toContain('overflow-hidden')
    expect(titlebarHeaderBaseClass).toContain('pr-[calc(var(--titlebar-tools-right')
    expect(titlebarHeaderBaseClass).toContain('var(--titlebar-tools-width')
    expect(titlebarHeaderBaseClass).not.toContain('pr-[max(0.75rem,var(--titlebar-tools-right')
  })
})
