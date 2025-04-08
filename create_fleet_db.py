
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    make TEXT,
    model TEXT,
    year INTEGER,
    mileage INTEGER,
    oil_change_due DATE,
    inspection_due DATE,
    notes TEXT,
    image_path TEXT,
    added_by INTEGER,
    FOREIGN KEY (added_by) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS service_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    service_date DATE NOT NULL,
    description TEXT,
    photo_path TEXT,
    added_by INTEGER,
    FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    FOREIGN KEY (added_by) REFERENCES users (id)
)
''')

conn.commit()
conn.close()
print("Fleet tables created successfully.")
