export const MISSION_CONTROL_PROJECT_LINK_CREATED = 'hermes:mission-control-project-link-created'
export const MISSION_CONTROL_PROJECT_CREATED = 'hermes:mission-control-project-created'

export interface MissionControlProjectCreatedDetail {
  projectId: string
  projectName: string
}

export interface MissionControlProjectLinkCreatedDetail {
  projectId: string
  sessionId: string
}

export function notifyMissionControlProjectCreated(detail: MissionControlProjectCreatedDetail) {
  window.dispatchEvent(new CustomEvent<MissionControlProjectCreatedDetail>(MISSION_CONTROL_PROJECT_CREATED, { detail }))
}

export function notifyMissionControlProjectLinkCreated(detail: MissionControlProjectLinkCreatedDetail) {
  window.dispatchEvent(new CustomEvent<MissionControlProjectLinkCreatedDetail>(MISSION_CONTROL_PROJECT_LINK_CREATED, { detail }))
}

