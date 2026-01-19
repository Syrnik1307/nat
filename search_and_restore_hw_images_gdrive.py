#!/usr/bin/env python
"""Search Google Drive for missing homework images and restore references.

This tries to recover legacy homework question images that used local /media/homework_files/ URLs.
If the files still exist on Google Drive (by filename), we attach them back to Question.config.

Run on server:
  cd /var/www/teaching_panel/teaching_panel
  source ../venv/bin/activate
  python search_and_restore_hw_images_gdrive.py
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")

import django  # noqa: E402

django.setup()  # noqa: E402

from homework.models import Question  # noqa: E402


# Map from Question.id -> expected filename (from historical broken URLs)
Q_TO_FILENAME = {
    94: "homework_teacher4_1768412910_92cffb0b_image.png",
    95: "homework_teacher4_1768412474_f90e5132_image.png",
    96: "homework_teacher4_1768412501_ef7f2921_image.png",
    97: "homework_teacher4_1768412535_0598717e_image.png",
    98: "homework_teacher4_1768412556_bb96e733_image.png",
    99: "homework_teacher4_1768412580_9d0d2941_image.png",
    100: "homework_teacher4_1768412634_e517ed23_image.png",
    101: "homework_teacher4_1768412676_0a5fc601_image.png",
    102: "homework_teacher4_1768412716_e80fdd8b_image.png",
    103: "homework_teacher4_1768412765_f19dffb2_image.png",
    104: "homework_teacher4_1768412816_b92f7b40_image.png",
    105: "homework_teacher4_1768412871_eba057a8_image.png",
    106: "homework_teacher4_1768413028_b4a86c99_image.png",
    107: "homework_teacher4_1768413063_aee9d5da_image.png",
    108: "homework_teacher4_1768413102_d8139c04_image.png",
}


def find_drive_file_id_by_exact_name(gdrive, filename: str):
    # Drive query: exact name match, not trashed.
    # Note: spaces='drive' is fine for My Drive; if using shared drives this may need supportsAllDrives.
    def _list(q: str):
        return (
            gdrive.service.files()
            .list(
                q=q,
                spaces="drive",
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields="files(id, name, mimeType, trashed)",
                pageSize=5,
            )
            .execute()
        )

    def _pick(files):
        if not files:
            return None
        for f in files:
            if (f.get("mimeType") or "").startswith("image/"):
                return f
        return files[0]

    try:
        # First: normal (not trashed)
        res = _list(f"name='{filename}' and trashed=false")
        picked = _pick(res.get("files", []))
        if picked:
            return picked

        # Second: search in trash
        res = _list(f"name='{filename}' and trashed=true")
        picked = _pick(res.get("files", []))
        if picked:
            return picked
        return None
    except Exception as e:
        print(f"[GDRIVE] query failed for {filename}: {e}")
        return None


def find_drive_candidates_by_contains(gdrive, needle: str, limit: int = 20):
    query = f"name contains '{needle}' and trashed=false"
    try:
        res = (
            gdrive.service.files()
            .list(
                q=query,
                spaces="drive",
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields="files(id, name, mimeType)",
                pageSize=min(max(limit, 1), 100),
            )
            .execute()
        )
        return res.get("files", [])
    except Exception as e:
        print(f"[GDRIVE] contains query failed for {needle}: {e}")
        return []


def main():
    from django.conf import settings

    if not getattr(settings, "USE_GDRIVE_STORAGE", False):
        print("USE_GDRIVE_STORAGE is disabled; cannot search Drive.")
        return

    try:
        from schedule.gdrive_utils import get_gdrive_manager

        gdrive = get_gdrive_manager()
    except Exception as e:
        print(f"Failed to init Google Drive manager: {e}")
        return

    # Diagnostics: see if ANY legacy names exist on Drive
    try:
        any_hits = find_drive_candidates_by_contains(gdrive, "homework_teacher4_", limit=25)
        print(f"Drive hits for 'homework_teacher4_': {len(any_hits)}")
        for f in any_hits[:10]:
            print(f"  - {f.get('name')} ({f.get('id')}) {f.get('mimeType')}")
    except Exception:
        pass

    restored = 0
    missing = []

    for q_id, filename in Q_TO_FILENAME.items():
        try:
            q = Question.objects.get(id=q_id)
        except Question.DoesNotExist:
            missing.append((q_id, filename, "question_not_found"))
            continue

        cfg = q.config if isinstance(q.config, dict) else {}

        # If already has a working imageFileId or https imageUrl - skip
        existing_url = (cfg.get("imageUrl") or "").strip()
        existing_id = (cfg.get("imageFileId") or "").strip()
        if existing_id or existing_url.startswith("https://"):
            continue

        picked = find_drive_file_id_by_exact_name(gdrive, filename)
        if not picked:
            # Try a weaker search by timestamp/hash chunks
            needle = filename.split("_image", 1)[0]
            candidates = find_drive_candidates_by_contains(gdrive, needle, limit=10)
            if candidates:
                missing.append((q_id, filename, f"file_not_found; candidates={[(c.get('name'), c.get('id')) for c in candidates[:3]]}"))
            else:
                missing.append((q_id, filename, "file_not_found"))
            continue

        file_id = picked.get("id")
        trashed = bool(picked.get("trashed"))

        # If in trash, try to restore it
        if trashed:
            try:
                gdrive.service.files().update(
                    fileId=file_id,
                    body={"trashed": False},
                    supportsAllDrives=True,
                    fields="id, trashed",
                ).execute()
                print(f"UNTRASHED: {filename} ({file_id})")
            except Exception as e:
                print(f"FAILED to untrash {filename} ({file_id}): {e}")

        try:
            cfg["imageFileId"] = file_id
            # Use direct download link from manager if available; fallback to uc?export=download
            direct = None
            try:
                direct = gdrive.get_direct_download_link(file_id)
            except Exception:
                direct = None
            cfg["imageUrl"] = direct or f"https://drive.google.com/uc?export=download&id={file_id}"

            q.config = cfg
            q.save(update_fields=["config"])
            restored += 1
            print(f"RESTORED Q{q_id}: {filename} -> {file_id}")
        except Exception as e:
            missing.append((q_id, filename, f"update_failed: {e}"))

    print("\n=== RESULT ===")
    print(f"Restored: {restored}")
    print(f"Missing: {len(missing)}")
    for item in missing[:50]:
        print(" - ", item)


if __name__ == "__main__":
    main()
