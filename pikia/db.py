import sqlite3

connection: sqlite3.Connection = sqlite3.connect("pikia.db")
cursor: sqlite3.Cursor = connection.cursor()


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
        "CREATE TABLE IF NOT EXISTS tags("
            "id INTEGER PRIMARY KEY,"
            "tagname VARCHAR(64) NOT NULL UNIQUE"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS file_tag("
            "id INTEGER PRIMARY KEY,"
            "file_id INTEGER,"
            "tag_id INTEGER,"
            "FOREIGN KEY(file_id) REFERENCES files(id),"
            "FOREIGN KEY(tag_id) REFERENCES tags(id)"
        ")"
    )


create_db()
