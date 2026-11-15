"""Single source of truth for the release version.

    python ci/get_version.py            -> prints e.g. 5.3.1 (from VERSION in wemo_ops_universal.py)
    python ci/get_version.py --check v5.3.1
        -> exits non-zero unless the tag, the desktop app VERSION, the server VERSION
           and the Dockerfile image label all agree. CI runs this before building,
           so a release can never ship with a mismatched update-check version.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # universal-app/


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def find(pattern, text, what):
    m = re.search(pattern, text, re.M)
    if not m:
        sys.exit(f"ERROR: could not find {what}")
    return m.group(1)


def versions():
    return {
        "wemo_ops_universal.py VERSION": find(r'^VERSION = "v([0-9][^"-]*)"', read("wemo_ops_universal.py"), "VERSION in wemo_ops_universal.py"),
        "wemo_server.py VERSION": find(r'^VERSION = "v([0-9][^"-]*)(?:-Server)?"', read("wemo_server.py"), "VERSION in wemo_server.py"),
        "Dockerfile image label": find(r'org\.opencontainers\.image\.version="([^"]+)"', read("Dockerfile"), "version label in Dockerfile"),
    }


def app_version():
    return find(r'^VERSION = "v([0-9][^"-]*)"', read("wemo_ops_universal.py"), "VERSION in wemo_ops_universal.py")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        found = versions()
        tag = sys.argv[2]
        expected = tag[1:] if tag.startswith("v") else tag
        bad = {k: v for k, v in found.items() if v != expected}
        for k, v in found.items():
            print(f"  {'OK ' if v == expected else 'BAD'} {k}: {v}")
        if bad:
            sys.exit(f"ERROR: tag {tag} does not match: " + ", ".join(bad) + ". Bump them all before tagging.")
        print(f"Version {expected} is consistent.")
        return
    # Plain lookup needs only the desktop app file, so partial copies can build
    print(app_version())


if __name__ == "__main__":
    main()
