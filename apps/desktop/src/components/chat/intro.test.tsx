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
    expect(screen.getByText('No saved chats yet')).toBeTruthy()
    expect(screen.getByText('Type below to start this project')).toBeTruthy()
  })

  it('shows recent project chat history from the selected project intro', () => {
    const onResumeProjectSession = vi.fn()

    render(
      <Intro
        onResumeProjectSession={onResumeProjectSession}
        projectId="project-hermes-mission-control"
        projectName="Hermes / Mission Control"
        projectOptions={[
          {
            id: 'project-hermes-mission-control',
            lastSessionId: 'session-latest',
            lastSessionTitle: 'Bridge smoke test',
            name: 'Hermes / Mission Control',
            sessionCount: 3
          },
          {
            id: 'project-tool-tally',
            lastSessionId: 'tool-session',
            lastSessionTitle: 'Wrong project',
            name: 'Tool & Tally',
            sessionCount: 1
          }
        ]}
        seed={0}
      />
    )

    expect(screen.getByText('3 chats')).toBeTruthy()
    expect(screen.getByText('Open latest: Bridge smoke test')).toBeTruthy()

    fireEvent.click(screen.getByText('Open latest: Bridge smoke test'))

    expect(onResumeProjectSession).toHaveBeenCalledWith(
      'session-latest',
      'project-hermes-mission-control',
      'Hermes / Mission Control'
    )
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
          {
            id: 'project-hermes-mission-control',
            lastSessionTitle: 'Bridge smoke test',
            name: 'Hermes / Mission Control',
            sessionCount: 2
          },
          { id: 'project-tool-tally', name: 'Tool & Tally' }
        ]}
        seed={0}
      />
    )

    expect(screen.getByLabelText('Projects').textContent).toContain('Projects')
    expect(screen.getByText('Pick a project')).toBeTruthy()
    expect(screen.getByText('Pick a project, then chat normally. Jenny gets the project brief and guardrails without extra copy/paste.')).toBeTruthy()
    expect(screen.getByText('2 chats')).toBeTruthy()
    expect(screen.getByText('Last: Bridge smoke test')).toBeTruthy()
    expect(screen.getByText('No chats yet')).toBeTruthy()
    expect(screen.getAllByText('Start project chat')).toHaveLength(2)

    fireEvent.click(screen.getByText('Hermes / Mission Control'))

    expect(onSelectProject).toHaveBeenCalledWith('project-hermes-mission-control', 'Hermes / Mission Control')

    fireEvent.click(screen.getByText('Create project'))

    expect(onCreateProject).toHaveBeenCalledOnce()
  })

  it('opens the latest project chat when a project already has sessions', () => {
    const onSelectProject = vi.fn()
    const onResumeProjectSession = vi.fn()

    render(
      <Intro
        onResumeProjectSession={onResumeProjectSession}
        onSelectProject={onSelectProject}
        projectOptions={[
          {
            id: 'project-hermes-mission-control',
            lastSessionId: 'session-latest',
            lastSessionTitle: 'Bridge smoke test',
            name: 'Hermes / Mission Control',
            sessionCount: 2
          }
        ]}
        seed={0}
      />
    )

    expect(screen.getByText('Open latest chat')).toBeTruthy()

    fireEvent.click(screen.getByText('Hermes / Mission Control'))

    expect(onResumeProjectSession).toHaveBeenCalledWith('session-latest', 'project-hermes-mission-control', 'Hermes / Mission Control')
    expect(onSelectProject).not.toHaveBeenCalled()
  })
})
