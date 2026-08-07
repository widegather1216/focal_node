import sqlite3
import json
import os
import re

db_path = os.path.expanduser("~/.config/focal_node_dev/focal_node.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT 
        i.id, 
        i.file_name, 
        i.file_path, 
        a.critique, 
        a.critique_updated_at,
        a.caption,
        a.tags,
        a.aesthetic_tags,
        m.camera_model,
        m.lens_model,
        m.f_number,
        m.shutter_speed,
        m.iso,
        m.focal_length
    FROM images i
    JOIN ai_analysis a ON i.id = a.image_id
    LEFT JOIN image_metadata m ON i.id = m.image_id
    WHERE a.critique IS NOT NULL AND a.critique != ''
    ORDER BY a.critique_updated_at DESC
""")

rows = cur.fetchall()
print(f"Total critiques in dev DB: {len(rows)}")

dev_db_data = []
for r in rows:
    dev_db_data.append({
        "id": r[0],
        "file_name": r[1],
        "file_path": r[2],
        "critique": r[3],
        "critique_updated_at": str(r[4]),
        "caption": r[5],
        "tags": r[6],
        "aesthetic_tags": r[7],
        "camera_model": r[8],
        "lens_model": r[9],
        "f_number": r[10],
        "shutter_speed": r[11],
        "iso": r[12],
        "focal_length": r[13]
    })

os.makedirs("scratch", exist_ok=True)
with open("scratch/current_dev_db_critiques_full.json", "w", encoding="utf-8") as f:
    json.dump(dev_db_data, f, ensure_ascii=False, indent=2)

print("Saved current dev db full records to scratch/current_dev_db_critiques_full.json")
for i, d in enumerate(dev_db_data):
    fn = d['file_name']
    img_id = d['id'][:8]
    print(f"\n==================== Photo #{i+1}: {fn} (ID: {img_id}) ====================")
    print(f"EXIF: {d['camera_model']} | {d['lens_model']} | F/{d['f_number']} | {d['shutter_speed']} | ISO {d['iso']} | {d['focal_length']}mm")
    print(f"Updated At: {d['critique_updated_at']}")
    print("--- CRITIQUE CONTENT ---")
    print(d["critique"])
