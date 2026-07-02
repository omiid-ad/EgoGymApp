
# GymEgo (مدیریت باشگاه EGO)

GymEgo is a lightweight, offline desktop application designed specifically for managing gym memberships, attendances, and financial plans. It provides a clean, web-based UI wrapped in a native Windows executable, completely eliminating the need for complex server setups or internet connectivity for the end-user.

## 🛠 Tech Stack

* **Backend / Native Wrapper:** Python 3, `pywebview`
* **Frontend:** Vanilla HTML, CSS, JavaScript
* **Database:** SQLite3
* **Bundler:** PyInstaller

## ⚙️ Development Setup

If you are setting this up in VS Code or Cursor, follow these steps to run the project locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/omiid-ad/EgoGymApp.git
    cd gym-ego
    ```

2.  **Set up the environment:**
    You can use standard `venv` or `uv` if you prefer a faster package installer:
    ```bash
    # Using standard venv
    python -m venv venv
    source venv/Scripts/activate  # Windows
    
    # Or using uv (recommended for speed)
    uv venv
    uv pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python main.py
    ```

## 🧠 Core Technical Details (Memory Aid)

This section contains architectural decisions and quirks to remember for future maintenance.

### 1. Database Architecture & Pathing
* **Location:** The SQLite database (`gym_database.sqlite`) does **not** live next to the `.exe` file. To ensure write permissions and prevent accidental deletion by non-expert users, it dynamically resolves to `%APPDATA%\GymEgo` on Windows (or `~/GymEgo` on Unix).
* **Schema:** The database handles `members`, `plans`, `attendance`, `payments`, and a key-value `settings` table (used for the auto-incrementing member `seq` and authentication).
* **State Management:** The frontend maintains a local JSON state (`db` object). When mutations occur (check-ins, new members), the JS calls `window.pywebview.api.save_db()`, which safely executes a batch `REPLACE`/`INSERT` to the SQLite backend.

### 2. PyInstaller & Asset Bundling
* Because `pywebview` needs to load a local HTML file, standard `--onefile` packaging will fail unless the HTML is bundled into PyInstaller's temporary `sys._MEIPASS` directory.
* **Build Command:** 
* ```bash
    pyinstaller --noconsole --onefile --icon=icon.ico --add-data "index.html;." main.py
    ```
* **Assets:** To avoid complex path resolutions for static files during the build, the Vazirmatn font and the favicon are **Base64 encoded** directly inside the `<style>` and `<link>` tags of `index.html`.

### 3. Authentication & Security
* The app features a lock screen with password protection and a recovery phrase.
* **Hashing:** Passwords are hashed on the client side (JavaScript) using a custom `Math.imul` bitwise hashing function before being sent to the Python backend. Plain text passwords are never stored in the SQLite `settings` table.

### 4. Check-in Logic
* The check-in mechanism strictly deducts 1 session upon entry. "Out times" were intentionally removed to streamline the UX. 
* Validations check if the user exists, if they have sessions left (`sessionsLeft > 0`), and if their plan hasn't expired (`expireAt` timestamp check).

## 🗃️ Backup and Restore
The application utilizes native OS file dialogs (via `webview.create_file_dialog`) to allow the user to export a copy of the SQLite database to a safe location, and restore it later. This entirely bypasses the need for the user to manually locate the `%APPDATA%` folder.

---
**Author:** Omid Adibfar  
**License:** MIT
