#!/usr/bin/env bash
# The seeded home, plus the sample LinkedIn export zipped the way LinkedIn sends it (files inside one folder).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../fixtures/seed.sh"
python3 - "$here/../fixtures/linkedin-export" <<'PY'
import pathlib, sys, zipfile
with zipfile.ZipFile("linkedin-export.zip", "w") as archive:
    for file in sorted(pathlib.Path(sys.argv[1]).iterdir()):
        archive.write(file, "Basic_LinkedInDataExport/" + file.name)
PY
