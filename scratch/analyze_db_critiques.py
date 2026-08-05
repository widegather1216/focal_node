import os
import sqlite3
import json

db_paths = [
    os.path.expanduser("~/.config/focal_node_dev/focal_node.db"),
    os.path.expanduser("~/.config/focal_node/focal_node.db"),
    "backend/focal_node.db",
]

target_db = None
for p in db_paths:
    if os.path.exists(p):
        print(f"Found DB at: {p}")
        target_db = p
        break

if not target_db:
    print("No DB found!")
    exit(1)

conn = sqlite3.connect(target_db)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

for t in tables:
    t_name = t[0]
    cursor.execute(f"PRAGMA table_info({t_name});")
    cols = cursor.fetchall()
    print(f"\nSchema for {t_name}: {[c[1] for c in cols]}")

# Fetch from ai_analysis and images
query = """
SELECT 
    i.id, 
    i.file_path, 
    a.caption,
    a.tags,
    a.aesthetic_tags,
    a.critique, 
    a.critique_updated_at,
    m.camera_model,
    m.lens_model
FROM images i
JOIN ai_analysis a ON i.id = a.image_id
LEFT JOIN image_metadata m ON i.id = m.image_id
WHERE a.critique IS NOT NULL AND a.critique != ''
ORDER BY a.critique_updated_at DESC
"""

cursor.execute(query)
rows = cursor.fetchall()
print(f"\nTotal critique records found: {len(rows)}")

critique_samples = []
for r in rows:
    img_id, file_path, caption, tags, aesthetic_tags, critique, updated_at, camera, lens = r
    critique_samples.append({
        "id": img_id,
        "file_path": file_path,
        "caption": caption,
        "tags": tags,
        "aesthetic_tags": aesthetic_tags,
        "critique": critique,
        "updated_at": updated_at,
        "camera": camera,
        "lens": lens
    })

print(f"Records with critique: {len(critique_samples)}")

with open("scratch/db_critiques_dump.json", "w", encoding="utf-8") as f:
    json.dump(critique_samples, f, ensure_ascii=False, indent=2)

print("Saved to scratch/db_critiques_dump.json")
