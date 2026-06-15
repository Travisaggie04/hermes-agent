export const MISSION_CONTROL_PROJECT_LINK_CREATED = 'hermes:mission-control-project-link-created'

export interface MissionControlProjectLinkCreatedDetail {
  projectId: string
  sessionId: string
}

export function notifyMissionControlProjectLinkCreated(detail: MissionControlProjectLinkCreatedDetail) {
  window.dispatchEvent(new CustomEvent<MissionControlProjectLinkCreatedDetail>(MISSION_CONTROL_PROJECT_LINK_CREATED, { detail }))
}

