import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Intro } from './intro'

afterEach(() => cleanup())

describe('Intro', () => {
  it('renders a clean project chat cue when a project is selected', () => {
    render(<Intro projectName="Hermes / Mission Control" seed={0} />)

    expect(screen.getByText('Project chat')).toBeTruthy()
    expect(screen.getByText('Hermes / Mission Control')).toBeTruthy()
    expect(screen.getByText('Talk to Jenny here. Project context and safety checks stay in the background.')).toBeTruthy()
  })

  it('keeps the generic intro when no project is selected', () => {
    render(<Intro personality="default" seed={0} />)

    expect(screen.queryByText('Project chat')).toBeNull()
    expect(screen.getByLabelText('HERMES AGENT')).toBeTruthy()
  })
})
