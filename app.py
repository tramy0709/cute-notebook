import os
from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

DB_NAME = os.path.join(os.getcwd(), "note.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            content TEXT
        )
    """)

    cursor.execute("SELECT * FROM notes WHERE id=1")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO notes (id, content) VALUES (1, '')")

    conn.commit()
    conn.close()


def get_note():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT content FROM notes WHERE id=1")
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else ""


def save_note(content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE notes SET content=? WHERE id=1", (content,))
    conn.commit()
    conn.close()


@app.route('/')
def cover():
    return render_template('cover.html')


@app.route('/note')
def note():
    note_content = get_note()
    return render_template('detail.html', note=note_content)


# 🔥 API auto save
@app.route('/save', methods=['POST'])
def auto_save():
    data = request.json
    content = data.get("content", "")
    save_note(content)
    return jsonify({"status": "saved"})


if __name__ == '__main__':
    init_db()
    app.run()