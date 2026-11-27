# Wiki source

This folder is the source of the [GitHub wiki](https://github.com/qrussell/wemo-ops-center/wiki). Don't edit the wiki on GitHub: every push to `main` copies this folder over it (`.github/workflows/wiki-sync.yml`), so changes made there are lost.

- One Markdown file per wiki page. The file name is the page name, with `-` for spaces (`Supported-Devices.md` is the "Supported Devices" page).
- `_Sidebar.md` and `_Footer.md` are the wiki's sidebar and footer.
- Link to another page as `[Troubleshooting](Troubleshooting.md)`, so the link works when browsing this folder. The sync turns it into the wiki's `Troubleshooting` link.
- Link to files in the repository and to images with full `https://github.com/qrussell/wemo-ops-center/...` URLs; relative paths don't work in the wiki.
- This `README.md` is not copied to the wiki.

Changes go through a merge request like any other change (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
