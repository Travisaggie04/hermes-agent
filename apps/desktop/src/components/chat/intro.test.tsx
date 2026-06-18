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
            recentSessions: [
              { id: 'session-latest', title: 'Bridge smoke test' },
              { id: 'session-planning', title: 'Planning review' }
            ],
            sessionCount: 3
          },
          {
            id: 'project-tool-tally',
            lastSessionId: 'tool-session',
            lastSessionTitle: 'Wrong project',
            name: 'Tool & Tally',
            recentSessions: [],
            sessionCount: 1
          }
        ]}
        seed={0}
      />
    )

    expect(screen.getByText('3 chats')).toBeTruthy()
    expect(screen.getByText('Open latest: Bridge smoke test')).toBeTruthy()
    expect(screen.getByText('Recent chats')).toBeTruthy()
    expect(screen.getByText('Bridge smoke test')).toBeTruthy()
    expect(screen.getByText('Planning review')).toBeTruthy()

    fireEvent.click(screen.getByText('Open latest: Bridge smoke test'))

    expect(onResumeProjectSession).toHaveBeenCalledWith(
      'session-latest',
      'project-hermes-mission-control',
      'Hermes / Mission Control'
    )

    fireEvent.click(screen.getByText('Planning review'))

    expect(onResumeProjectSession).toHaveBeenCalledWith(
      'session-planning',
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
            lastSessionId: '',
            lastSessionTitle: 'Bridge smoke test',
            name: 'Hermes / Mission Control',
            recentSessions: [],
            sessionCount: 2
          },
          { id: 'project-tool-tally', lastSessionId: '', lastSessionTitle: '', name: 'Tool & Tally', recentSessions: [], sessionCount: 0 }
        ]}
        seed={0}
      />
    )

    expect(screen.getByLabelText('Projects').textContent).toContain('Projects')
    expect(screen.getByText('Pick a project')).toBeTruthy()
    expect(screen.getByText('Pick a project, then chat normally. Jenny gets the right project context without extra copy/paste.')).toBeTruthy()
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
            recentSessions: [],
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

  it('shows unfiled Other chats on the blank native chat home', () => {
    const onResumeOtherSession = vi.fn()

    render(
      <Intro
        onResumeOtherSession={onResumeOtherSession}
        otherChatCount={2}
        otherChats={[
          { id: 'legacy-root', title: 'Legacy planning chat' },
          { id: 'scratch-root', title: 'Scratch notes' }
        ]}
        seed={0}
      />
    )

    expect(screen.getByText('Pick a project')).toBeTruthy()
    expect(screen.getByText('Other chats')).toBeTruthy()
    expect(screen.getByText('2 unfiled chats')).toBeTruthy()
    expect(screen.getByText('Legacy planning chat')).toBeTruthy()

    fireEvent.click(screen.getByText('Legacy planning chat'))

    expect(onResumeOtherSession).toHaveBeenCalledWith('legacy-root')
  })
})
