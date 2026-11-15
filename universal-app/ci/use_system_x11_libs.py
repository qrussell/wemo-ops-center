"""Make a PyInstaller spec use the distribution's X11/font libraries instead of
bundling the build machine's copies.

    python ci/use_system_x11_libs.py wemo-ops-client.spec

Why: PyInstaller copies the build machine's libXft/fontconfig/freetype into the
app. Built on Rocky 9 (libXft 2.3.3) the GUI crashed on Fedora 40 at startup
whenever a color emoji font was installed ("X Error BadLength ...
RenderAddGlyphs", a bug fixed in libXft 2.3.5), and on Fedora 45 the old
fontconfig could not parse the system font config (45 warnings, broken font
matching). Loading the system's own copies fixed both.

The excluded libraries are declared as package dependencies instead (see
build_rpm.sh / build_deb.sh). Their whole dependency chain is excluded too: the
bundled copies would otherwise be found first through PyInstaller's
LD_LIBRARY_PATH and mix old and new versions. Pillow's private copies
(hashed names like libfreetype-57f805ba.so.6) are unaffected.
"""
import re
import sys

SYSTEM_LIBS = (
    # X11 client stack
    "libX11.so", "libX11-xcb.so", "libxcb.so", "libXau.so", "libXdmcp.so", "libXrender.so",
    # font rendering stack used by Tk
    "libXft.so", "libfontconfig.so", "libfreetype.so",
    # their dependencies
    "libharfbuzz.so", "libgraphite2.so", "libpng16.so", "libbrotlicommon.so",
    "libbrotlidec.so", "libglib-2.0.so", "libpcre.so", "libpcre2-8.so", "libexpat.so",
)

FILTER = f'''
# --- added by ci/use_system_x11_libs.py: use the distribution's X11/font libraries
import os as _os
_SYSTEM_LIBS = {SYSTEM_LIBS!r}
a.binaries = [b for b in a.binaries if not _os.path.basename(b[0]).startswith(_SYSTEM_LIBS)]
'''


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        spec = f.read()
    if "use_system_x11_libs" in spec:
        return
    m = re.search(r"^pyz = PYZ\(", spec, re.M)
    if not m:
        sys.exit(f"ERROR: no 'pyz = PYZ(' line in {path}; PyInstaller spec format changed?")
    spec = spec[:m.start()] + FILTER + "\n" + spec[m.start():]
    with open(path, "w", encoding="utf-8") as f:
        f.write(spec)
    print(f"   > {path}: using system X11/font libraries")


if __name__ == "__main__":
    main()
