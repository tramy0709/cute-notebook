from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
DB_NAME = "note.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, content TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS redo (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        task TEXT
    )
    """)
    cursor.execute("SELECT * FROM notes WHERE id=1")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO notes (id, content) VALUES (1, '')")
        cursor.execute("INSERT INTO history (content) VALUES ('')")
    conn.commit()
    conn.close()

# ================== ROUTES CỦA TRAMY ==================

@app.route('/')
def home():
    # SỬA LỖI: Trả về trang bìa trước tiên
    return render_template('cover.html')

@app.route('/note')
def note():
    conn = get_db_connection()
    result = conn.execute("SELECT content FROM notes WHERE id=1").fetchone()
    conn.close()
    note_content = result['content'] if result else ""
    return render_template('detail.html', note=note_content)

@app.route('/save', methods=['POST'])
def auto_save():
    data = request.json
    content = data.get("content", "")
    conn = get_db_connection()
    conn.execute("DELETE FROM redo")
    conn.execute("INSERT INTO history (content) VALUES (?)", (content,))
    conn.execute("UPDATE notes SET content=? WHERE id=1", (content,))
    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})

@app.route('/undo', methods=['POST'])
def undo():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, content FROM history ORDER BY id DESC LIMIT 2").fetchall()
    if len(rows) < 2:
        conn.close()
        return jsonify({"content": rows[0]['content'] if rows else ""})
    
    current_id, current_content = rows[0]['id'], rows[0]['content']
    previous_content = rows[1]['content']
    
    conn.execute("INSERT INTO redo (content) VALUES (?)", (current_content,))
    conn.execute("DELETE FROM history WHERE id=?", (current_id,))
    conn.execute("UPDATE notes SET content=? WHERE id=1", (previous_content,))
    conn.commit()
    conn.close()
    return jsonify({"content": previous_content})

@app.route('/redo', methods=['POST'])
def redo():
    conn = get_db_connection()
    row = conn.execute("SELECT id, content FROM redo ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        conn.execute("INSERT INTO history (content) VALUES (?)", (row['content'],))
        conn.execute("UPDATE notes SET content=? WHERE id=1", (row['content'],))
        conn.execute("DELETE FROM redo WHERE id=?", (row['id'],))
        conn.commit()
        conn.close()
        return jsonify({"content": row['content']})
    conn.close()
    return jsonify({"content": ""})

# ================== PHẦN LỊCH HẸN ==================

@app.route('/schedule')
def schedule():
    conn = get_db_connection()
    # Sắp xếp theo ngày tăng dần
    items = conn.execute("SELECT * FROM appointments ORDER BY date ASC, time ASC").fetchall()
    conn.close()
    return render_template('schedule.html', appointments=items)

@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    data = request.json
    date = data.get("date")
    time = data.get("time")
    task = data.get("task", "") 

    if not date or not time:
        return jsonify({"status": "error", "message": "Thiếu ngày hoặc giờ"}), 400

    conn = get_db_connection()
    conn.execute("INSERT INTO appointments (date, time, task) VALUES (?, ?, ?)", (date, time, task))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/delete_schedule/<int:id>', methods=['DELETE'])
def delete_schedule(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM appointments WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)