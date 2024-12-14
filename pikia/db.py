import sqlite3
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core import ImageAnalysis

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
            "file_id INTEGER,"
            "label_id INTEGER,"
            "weight REAL,"
            "FOREIGN KEY(file_id) REFERENCES files(id),"
            "FOREIGN KEY(label_id) REFERENCES labels(id),"
            "PRIMARY KEY(file_id, label_id)"
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
    cursor.execute("INSERT OR IGNORE INTO file_label(file_id, label_id, weight) VALUES (?, ?, ?)", [file_id, label_id, weight])
    connection.commit()

def insert_analysis(analysis_list: list['ImageAnalysis']):
    # List and insert labels
    labels = [
        detection.label
        for analysis in analysis_list
        for detection in analysis.get_top_detections()
    ]
    insert_labels(labels)
    
    # Insert relations between each file and each label
    for analysis in analysis_list:
        for detection in analysis.get_top_detections():
            insert_file_label_relation(analysis.filename, detection.label, detection.weight)

def select_labels_by_frequency():
    return cursor.execute("select labels.labelname, count(file_label.label_id) as times from labels, file_label where file_label.label_id = labels.id group by file_label.label_id order by times desc").fetchall()

def select_images_with_best_label(labels: list[str]):
    if len(labels) == 0:
        return []
    
    return cursor.execute(
        """
        WITH RankedLabels AS (
            SELECT f.id AS file_id, f.filepath, l.id as label_id, l.labelname, fl.weight,
                ROW_NUMBER() OVER (PARTITION BY f.id ORDER BY fl.weight DESC) AS rank
            FROM files f
            INNER JOIN file_label fl ON f.id = fl.file_id
            INNER JOIN labels l ON fl.label_id = l.id
            WHERE l.labelname IN ({seq})
        )
        SELECT file_id, filepath, label_id, labelname
        FROM RankedLabels
        WHERE rank = 1
        """.format(seq=",".join("?" * len(labels))),
        labels).fetchall()

def select_images_with_final_label():
    return cursor.execute("SELECT files.id, files.filepath, labels.labelname FROM files INNER JOIN labels ON files.final_label = labels.id").fetchall()

def select_total_file_count():
    return cursor.execute("SELECT COUNT(*) FROM files").fetchone()[0]

def update_final_labels(final_labels: list[tuple[int, int]]):
    cursor.executemany("UPDATE files SET final_label = ? WHERE id = ?", final_labels)
    connection.commit()
