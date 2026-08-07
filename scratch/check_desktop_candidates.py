import os
import sqlite3

db_path = os.path.expanduser("~/.config/focal_node_dev/focal_node.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT i.id, i.file_name, i.file_path, a.critique, m.camera_model, m.f_number, m.shutter_speed, m.iso, m.focal_length
    FROM images i
    LEFT JOIN ai_analysis a ON i.id = a.image_id
    LEFT JOIN image_metadata m ON i.id = m.image_id
    WHERE i.file_path LIKE '%/Desktop/photo/jpeg/%'
    ORDER BY i.file_name
""")
rows = cur.fetchall()
print(f"Total photos in DB from Desktop/photo/jpeg: {len(rows)}")
for r in rows[:15]:
    has_critique = "YES" if (r[3] and len(r[3]) > 10) else "NO"
    print(f"- {r[1]} | HasCritique: {has_critique} | EXIF: F/{r[5]}, {r[6]}s, ISO {r[7]}, {r[8]}mm")
