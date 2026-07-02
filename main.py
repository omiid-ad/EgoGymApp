import webview
import sqlite3
import os
import shutil
from datetime import datetime


def get_app_data_path():
    # Resolves to C:\Users\<User>\AppData\Roaming\GymEgo on Windows
    app_data = os.getenv("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")

    app_dir = os.path.join(app_data, "GymEgo")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "gym_database.sqlite")


DB_FILE = get_app_data_path()


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY, code TEXT, fName TEXT, lName TEXT, phone TEXT, nationalCode TEXT, birth TEXT, emg TEXT, note TEXT, joinedAt INTEGER, planId INTEGER, sessionsLeft INTEGER, expireAt INTEGER)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY, name TEXT, sessions INTEGER, days INTEGER, price REAL)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, memberId INTEGER, date TEXT, in_time INTEGER)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, memberId INTEGER, planId INTEGER, amount REAL, at_time INTEGER)"
        )
        conn.commit()


class GymApi:
    def load_db(self):
        db_state = {
            "seq": 10000,
            "members": [],
            "plans": [],
            "attendance": [],
            "payments": [],
        }
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("SELECT * FROM settings WHERE key='seq'")
            seq_row = c.fetchone()
            if seq_row:
                db_state["seq"] = int(seq_row["value"])

            c.execute("SELECT * FROM members")
            db_state["members"] = [dict(row) for row in c.fetchall()]

            c.execute("SELECT * FROM plans")
            db_state["plans"] = [dict(row) for row in c.fetchall()]

            c.execute("SELECT memberId, date, in_time as 'in' FROM attendance")
            db_state["attendance"] = [dict(row) for row in c.fetchall()]

            c.execute("SELECT memberId, planId, amount, at_time as 'at' FROM payments")
            db_state["payments"] = [dict(row) for row in c.fetchall()]
        return db_state

    def save_db(self, db_state):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "REPLACE INTO settings (key, value) VALUES ('seq', ?)",
                (str(db_state["seq"]),),
            )

            c.execute("DELETE FROM members")
            for m in db_state["members"]:
                c.execute(
                    """INSERT INTO members (id, code, fName, lName, phone, nationalCode, birth, emg, note, joinedAt, planId, sessionsLeft, expireAt) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        m["id"],
                        m["code"],
                        m["fName"],
                        m["lName"],
                        m["phone"],
                        m.get("nationalCode"),
                        m.get("birth"),
                        m.get("emg"),
                        m.get("note"),
                        m["joinedAt"],
                        m.get("planId"),
                        m["sessionsLeft"],
                        m.get("expireAt"),
                    ),
                )

            c.execute("DELETE FROM plans")
            for p in db_state["plans"]:
                c.execute(
                    "INSERT INTO plans (id, name, sessions, days, price) VALUES (?, ?, ?, ?, ?)",
                    (p["id"], p["name"], p["sessions"], p["days"], p["price"]),
                )

            c.execute("DELETE FROM attendance")
            for a in db_state["attendance"]:
                c.execute(
                    "INSERT INTO attendance (memberId, date, in_time) VALUES (?, ?, ?)",
                    (a["memberId"], a["date"], a["in"]),
                )

            c.execute("DELETE FROM payments")
            for p in db_state["payments"]:
                c.execute(
                    "INSERT INTO payments (memberId, planId, amount, at_time) VALUES (?, ?, ?, ?)",
                    (p["memberId"], p["planId"], p["amount"], p["at"]),
                )
            conn.commit()
        return True

    # --- Authentication Flow ---
    def check_auth_setup(self):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key='password'")
            return {"has_pw": c.fetchone() is not None}

    def setup_auth(self, pw_hash, recovery_phrase):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "REPLACE INTO settings (key, value) VALUES ('password', ?)", (pw_hash,)
            )
            c.execute(
                "REPLACE INTO settings (key, value) VALUES ('recovery', ?)",
                (recovery_phrase.lower().strip(),),
            )
            conn.commit()
        return True

    def verify_auth(self, pw_hash):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key='password'")
            row = c.fetchone()
            return row and row[0] == pw_hash

    def recover_auth(self, phrase, new_pw_hash):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key='recovery'")
            row = c.fetchone()
            if row and row[0] == phrase.lower().strip():
                c.execute(
                    "REPLACE INTO settings (key, value) VALUES ('password', ?)",
                    (new_pw_hash,),
                )
                conn.commit()
                return True
        return False

    def change_password(self, new_pw_hash):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "REPLACE INTO settings (key, value) VALUES ('password', ?)",
                (new_pw_hash,),
            )
            conn.commit()
        return True

    # --- Native OS File Handling ---
    def trigger_backup(self):
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory="",
            save_filename=f'gym-backup-{datetime.now().strftime("%Y-%m-%d")}.sqlite',
        )
        if result:
            shutil.copy2(DB_FILE, result[0])
            return True
        return False

    def trigger_restore(self):
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory="",
            allow_multiple=False,
            file_types=("SQLite Files (*.sqlite)", "All Files (*.*)"),
        )
        if result:
            shutil.copy2(result[0], DB_FILE)
            return self.load_db()
        return None


if __name__ == "__main__":
    init_db()
    api = GymApi()

    # Resolves the absolute path to index.html next to the executable
    html_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

    webview.create_window(
        "مدیریت باشگاه بانوان", html_file, js_api=api, width=1050, height=800
    )
    webview.start()
