import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Intro } from './intro'

afterEach(() => cleanup())

describe('Intro', () => {
  it('renders a clean project chat cue when a project is selected', () => {
    render(<Intro projectName="Hermes / Mission Control" seed={0} />)

    expect(screen.getByText('Project chat')).toBeTruthy()
    expect(screen.getByText('Hermes / Mission Control')).toBeTruthy()
    expect(screen.getByText('Send normally. Jenny replies here, with project context and safety checks in the background.')).toBeTruthy()
  })

  it('keeps the generic intro when no project is selected', () => {
    render(<Intro personality="default" seed={0} />)

    expect(screen.queryByText('Project chat')).toBeNull()
    expect(screen.getByLabelText('HERMES AGENT')).toBeTruthy()
  })

  it('turns the blank native chat home into a project picker when projects exist', () => {
    const onSelectProject = vi.fn()
    const onCreateProject = vi.fn()

    render(
      <Intro
        onCreateProject={onCreateProject}
        onSelectProject={onSelectProject}
        projectOptions={[
          { id: 'project-hermes-mission-control', name: 'Hermes / Mission Control' },
          { id: 'project-tool-tally', name: 'Tool & Tally' }
        ]}
        seed={0}
      />
    )

    expect(screen.getByLabelText('Jenny projects').textContent).toContain('Jenny projects')
    expect(screen.getByText('Pick a project')).toBeTruthy()
    expect(screen.getByText('Pick a project, then chat normally. Jenny gets the project brief and guardrails without extra copy/paste.')).toBeTruthy()

    fireEvent.click(screen.getByText('Hermes / Mission Control'))

    expect(onSelectProject).toHaveBeenCalledWith('project-hermes-mission-control', 'Hermes / Mission Control')

    fireEvent.click(screen.getByText('Create Jenny project'))

    expect(onCreateProject).toHaveBeenCalledOnce()
  })
})
