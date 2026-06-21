import type { HermesConnection } from '@/global'

export const TITLEBAR_HEIGHT = 34
export const MACOS_TRAFFIC_LIGHTS_HEIGHT = 14
export const TITLEBAR_ICON_SIZE = 12
export const TITLEBAR_CONTROL_OFFSET_X = 74
export const TITLEBAR_CONTROL_HEIGHT = 22
export const TITLEBAR_CONTROLS_TOP = (TITLEBAR_HEIGHT - TITLEBAR_CONTROL_HEIGHT) / 2
export const TITLEBAR_FALLBACK_WINDOW_BUTTON_X = 24
// Edge inset used when no left-side native controls take up that space —
// Windows/Linux (native overlay is on the right) and macOS fullscreen
// (traffic lights are hidden). Matches the right-cluster's 0.75rem padding.
export const TITLEBAR_EDGE_INSET = 14

// Titlebar palette only. All sizing/radius/cursor/centering come from the
// shared <Button size="icon-titlebar"> (used polymorphically via asChild) —
// Button is the single source of button styling.
export const titlebarButtonClass =
  'text-muted-foreground/85 hover:bg-(--ui-control-hover-background) hover:text-foreground'

// Page headers share the draggable titlebar strip with fixed app/native
// controls. Reserve the left traffic-light/sidebar space separately from the
// fixed right tools/window-controls area so header content cannot paint under
// either edge when it gets crowded.
export const titlebarHeaderBaseClass =
  'pointer-events-none relative z-3 flex h-(--titlebar-height) shrink-0 items-center justify-start gap-3 overflow-hidden border-b border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) pl-[max(0.75rem,var(--titlebar-content-inset,0rem),calc(var(--titlebar-left-safe-inset,0rem)-var(--titlebar-left-pane-width,0px)))] pr-[calc(var(--titlebar-tools-right,0rem)+var(--titlebar-tools-width,0rem)+0.75rem)]'

export const titlebarHeaderShadowClass =
  "after:pointer-events-none after:absolute after:left-0 after:right-0 after:top-full after:h-4 after:bg-linear-to-b after:from-(--ui-chat-surface-background) after:to-transparent after:content-['']"

export function titlebarControlsPosition(
  windowButtonPosition: HermesConnection['windowButtonPosition'] | undefined,
  isFullscreen = false
) {
  const top = Math.max(0, TITLEBAR_CONTROLS_TOP)

  // No left-side native controls to dodge:
  //   - Windows/Linux: native min/max/close render on the right via titleBarOverlay.
  //   - macOS fullscreen: traffic lights are hidden.
  // In both cases, pin the cluster to the edge with a small inset.
  if (windowButtonPosition === null || isFullscreen) {
    return { left: TITLEBAR_EDGE_INSET, top }
  }

  return {
    left: (windowButtonPosition?.x ?? TITLEBAR_FALLBACK_WINDOW_BUTTON_X) + TITLEBAR_CONTROL_OFFSET_X,
    top
  }
}
