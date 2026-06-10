import { describe, expect, it } from 'vitest'

import { APP_ROUTES, appViewForPath, MISSION_CONTROL_ROUTE } from './routes'

describe('Mission Control desktop route', () => {
  it('appears in the route table and resolves to the Mission Control view', () => {
    expect(APP_ROUTES).toContainEqual({ id: 'mission-control', path: MISSION_CONTROL_ROUTE, view: 'mission-control' })
    expect(appViewForPath('/mission-control')).toBe('mission-control')
  })
})
