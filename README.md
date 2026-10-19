# Caliper

Native Windows STL visualization, on-demand analysis and independent repair.

## Download for Windows x64

**[Download Caliper-Setup.exe](https://github.com/SynrgStudio/caliperreleases/releases/latest/download/Caliper-Setup.exe)**

[All releases and portable downloads](https://github.com/SynrgStudio/caliperreleases/releases)

Installers are attached to GitHub Releases, not committed to this repository. The stable installer is always named **Caliper-Setup.exe**; its version is identified by the release tag and installer metadata. Extract the complete ZIP to use the portable application. Python is not required.

Caliper is **free to access**. Donations are optional and do not buy access to the app. Application source is **closed for now** and is maintained separately in a private repository. This public repository contains distribution information only, not application source. Any future open-source release will be an explicit owner decision.

## Updates and safety

Recent builds can check stable releases in the background. Use **View → Check for updates / Ctrl+U** to check manually. A newer version offers a download; size, GitHub SHA-256 and installer product/version metadata are checked before Windows opens setup with your confirmation. Save work and finish pending operations first. Older builds without this updater need one manual installation. `--no-updates` disables startup checks.

Current binaries are **not digitally signed**. Windows may display **Unknown publisher / SmartScreen**. Checksums verify byte integrity, not a code-signing identity; do not disable security protections to install. Download only the assets in this repository's releases and compare against `SHA256SUMS.txt`.

Setup is per-user, preserves upgrade/preferences compatibility and does not force the default STL application. Close Caliper normally before installation. Repair keeps the source unchanged; save a copy for the repaired result. Finite resource limits apply; analysis and repair are not a printability certification.
