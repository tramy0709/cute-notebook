from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

DB_NAME = "note.db"

# ================== INIT DB ==================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Bảng note chính
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        content TEXT
    )
    """)

    # Bảng history (để undo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT
    )
    """)

    # Bảng redo (để redo) - MỚI
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS redo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT
    )
    """)

    # Tạo note mặc định nếu chưa có
    cursor.execute("SELECT * FROM notes WHERE id=1")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO notes (id, content) VALUES (1, '')")
        # Lưu bản ghi đầu tiên vào history để có mốc undo
        cursor.execute("INSERT INTO history (content) VALUES ('')")

    conn.commit()
    conn.close()


# ================== GET NOTE ==================
def get_note():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM notes WHERE id=1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else ""


# ================== ROUTES ==================

@app.route('/')
def home():
    return render_template('cover.html')


@app.route('/note')
def note():
    note_content = get_note()
    return render_template('detail.html', note=note_content)


# AUTO SAVE
@app.route('/save', methods=['POST'])
def auto_save():
    data = request.json
    content = data.get("content", "")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Khi có thay đổi mới, các hành động Redo cũ không còn giá trị -> Xóa Redo
    cursor.execute("DELETE FROM redo")
    
    # Lưu vào history
    cursor.execute("INSERT INTO history (content) VALUES (?)", (content,))
    
    # Update note hiện tại
    cursor.execute("UPDATE notes SET content=? WHERE id=1", (content,))

    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})


# UNDO
@app.route('/undo', methods=['POST'])
def undo():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Lấy 2 bản ghi gần nhất từ history (hiện tại và trước đó)
    cursor.execute("SELECT id, content FROM history ORDER BY id DESC LIMIT 2")
    rows = cursor.fetchall()

    if len(rows) < 2:
        conn.close()
        return jsonify({"content": rows[0][1] if rows else ""})

    current_id = rows[0][0]
    current_content = rows[0][1]
    previous_content = rows[1][1]

    # Đưa nội dung hiện tại vào Redo
    cursor.execute("INSERT INTO redo (content) VALUES (?)", (current_content,))
    
    # Xóa nội dung hiện tại khỏi history
    cursor.execute("DELETE FROM history WHERE id=?", (current_id,))
    
    # Cập nhật note chính về bản ghi cũ hơn
    cursor.execute("UPDATE notes SET content=? WHERE id=1", (previous_content,))
    
    conn.commit()
    conn.close()
    return jsonify({"content": previous_content})


# REDO
@app.route('/redo', methods=['POST'])
def redo():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Lấy bản ghi cuối cùng trong bảng Redo
    cursor.execute("SELECT id, content FROM redo ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    if row:
        redo_id = row[0]
        redo_content = row[1]

        # Đưa nội dung này quay lại history
        cursor.execute("INSERT INTO history (content) VALUES (?)", (redo_content,))
        
        # Cập nhật vào note chính
        cursor.execute("UPDATE notes SET content=? WHERE id=1", (redo_content,))
        
        # Xóa khỏi bảng redo
        cursor.execute("DELETE FROM redo WHERE id=?", (redo_id,))
        
        conn.commit()
        conn.close()
        return jsonify({"content": redo_content})

    conn.close()
    return jsonify({"content": get_note()})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)