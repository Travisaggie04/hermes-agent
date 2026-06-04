from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_TS = ROOT / "web" / "src" / "lib" / "api.ts"
PANEL_TSX = ROOT / "web" / "src" / "components" / "ArtifactWorkspaceBrowser.tsx"
MISSION_TSX = ROOT / "web" / "src" / "pages" / "MissionControlPage.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_artifact_workspace_browser_api_helper_uses_read_only_route():
    source = _read(API_TS)

    assert "listMissionControlArtifacts" in source
    assert 'fetchJSON<MissionControlArtifactListResponse>("/api/mission-control/artifacts", { cache: "no-store" })' in source
    assert "MissionControlArtifact" in source
    assert "MissionControlArtifactListResponse" in source

    helper_block = source[source.index("listMissionControlArtifacts") : source.index("listMissionBriefs")]
    assert "method:" not in helper_block
    assert "POST" not in helper_block
    assert "PUT" not in helper_block
    assert "DELETE" not in helper_block


def test_artifact_workspace_browser_renders_metadata_only_safety_posture():
    source = _read(PANEL_TSX)

    for phrase in (
        "Artifact / Workspace Browser",
        "Untrusted metadata",
        "Inert context only",
        "Not trusted for execution",
        "No artifact metadata recorded.",
        "Could not load artifact metadata",
        "source_ref_count",
        "trusted_for_execution",
        "inert_context_only",
        "untrusted",
    ):
        assert phrase in source

    assert "api.listMissionControlArtifacts" in source
    assert "useEffect" in source


def test_artifact_workspace_browser_does_not_expose_open_preview_download_or_mutations():
    source = _read(PANEL_TSX)

    forbidden_visible_text = (
        ">Run<",
        ">Execute<",
        ">Delete<",
        ">Open<",
        ">Download<",
        ">Preview<",
        ">Dispatch<",
        ">Create<",
        ">Edit<",
        ">Launch<",
        ">Start<",
        ">Sync<",
        ">Publish<",
        ">Refresh<",
    )
    for label in forbidden_visible_text:
        assert label not in source

    forbidden_code = (
        "window.open",
        "href=",
        "download",
        "getMissionControlPacket",
        "getProjectRoomAttachment",
        "downloadProjectRoomAttachment",
        "createMission",
        "updateMission",
        "archiveMission",
        "addProjectRoomMessage",
        "uploadProjectRoomAttachment",
        "fetch(",
        "method:",
        "POST",
        "PUT",
        "DELETE",
    )
    for token in forbidden_code:
        assert token not in source


def test_mission_control_page_mounts_artifact_workspace_browser():
    source = _read(MISSION_TSX)

    assert "ArtifactWorkspaceBrowser" in source
    assert "<ArtifactWorkspaceBrowser />" in source
