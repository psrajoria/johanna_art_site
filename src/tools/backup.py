"""
Make a backup of everything that can't be rebuilt from git: the database,
uploaded images and private downloads.

    python tools/backup.py /backups

Creates /backups/johanna-YYYYmmdd-HHMM.tar.gz. Copy that file somewhere safe
(see docs/DEPLOY.md). To restore, see the same document.
"""

import os
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

DB = Path(os.environ.get("DATABASE_PATH", "db.sqlite3"))
MEDIA = Path(os.environ.get("MEDIA_ROOT", "media"))
PRIVATE = Path(os.environ.get("PRIVATE_MEDIA_ROOT", "private_media"))


def main(target_dir):
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    archive = target / f"johanna-{stamp}.tar.gz"

    with tempfile.TemporaryDirectory() as tmp:
        # sqlite3's backup API gives a consistent copy even while the site is running
        snapshot = Path(tmp) / "db.sqlite3"
        source = sqlite3.connect(DB)
        dest = sqlite3.connect(snapshot)
        with dest:
            source.backup(dest)
        dest.close()
        source.close()

        with tarfile.open(archive, "w:gz") as tar:
            tar.add(snapshot, arcname="db.sqlite3")
            for folder, name in ((MEDIA, "media"), (PRIVATE, "private_media")):
                if folder.exists():
                    tar.add(folder, arcname=name)

    print(f"Backup written: {archive} ({archive.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "backups")
