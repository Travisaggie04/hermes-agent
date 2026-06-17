import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_windows_installer_is_english_only() -> None:
    package_json = json.loads((REPO_ROOT / "apps" / "desktop" / "package.json").read_text(encoding="utf-8"))

    nsis_config = package_json["build"]["nsis"]

    assert nsis_config["multiLanguageInstaller"] is False
    assert nsis_config["installerLanguages"] == ["en_US"]
    assert "zh_CN" not in nsis_config["installerLanguages"]
    assert "zh_TW" not in nsis_config["installerLanguages"]
