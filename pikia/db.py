import sqlite3

connection: sqlite3.Connection = sqlite3.connect("pikia.db")
cursor: sqlite3.Cursor = connection.cursor()

class RelationshipError(Exception):
    pass

def create_db() -> None:
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS files("
            "id INTEGER PRIMARY KEY,"
            "filepath VARCHAR(1000) NOT NULL UNIQUE,"
            "caption VARCHAR(128),"
            "detailed_caption VARCHAR(256),"
            "more_detailed_caption VARCHAR(512),"
            "processed BOOLEAN NOT NULL DEFAULT 0,"
            "final_label INTEGER,"
            "FOREIGN KEY(final_label) REFERENCES labels(id)"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS labels("
            "id INTEGER PRIMARY KEY,"
            "labelname VARCHAR(64) NOT NULL UNIQUE"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS file_label("
            "id INTEGER PRIMARY KEY,"
            "file_id INTEGER,"
            "label_id INTEGER,"
            "weight REAL,"
            "FOREIGN KEY(file_id) REFERENCES files(id),"
            "FOREIGN KEY(label_id) REFERENCES labels(id)"
        ")"
    )


create_db()


def insert_imagefiles(filenames: list[str]):
    filenames = [(filename,) for filename in filenames]
    cursor.executemany("INSERT INTO files(filepath) VALUES (?)", filenames)
    connection.commit()

def insert_labels(labels: list[str]):
    labels = [(label,) for label in labels]
    cursor.executemany("INSERT OR IGNORE INTO labels(labelname) VALUES (?)", labels)
    connection.commit()

def insert_file_label_relation(filename: str, label: str, weight: int):
    result = cursor.execute("SELECT files.id, labels.id FROM files, labels WHERE files.filepath = ? AND labels.labelname = ?", [filename, label]).fetchone()
    if result is None:
        raise RelationshipError(f"Missing row for file '{filename}' or label '{label}'")
    
    file_id, label_id = result
    cursor.execute("INSERT INTO file_label(file_id, label_id, weight) VALUES (?, ?, ?)", [file_id, label_id, weight])
    connection.commit()

    