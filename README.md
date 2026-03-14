# PuTTY Connection Manager (PCM) 🚀

**PuTTY Connection Manager (PCM)** is a lightweight, Python-based open-source tool designed to manage SSH sessions efficiently. It serves as a powerful graphical interface (GUI) for PuTTY, adding essential features like a flexible folder structure, real-time search, and a modern, customizable UI.



## ✨ Features

* 📁 **Unlimited Folder Structure:** Organize your servers into logical groups.
* 🌓 **Built-in Theme System:** Toggle between Light Mode and Dark Mode with a single click.
* 🔍 **Real-time Search:** Instantly find connections as you type.
* 🖱️ **Drag & Drop:** Intuitively move servers between folders.
* 📥 **CSV Import:** Support for bulk imports.
* 🗄️ **Local Database:** All data is stored in `connections.db`.
* ⚡ **Quick Launch:** Double-click to open a PuTTY session.

## 🛠️ Installation & Setup

### 1. Prerequisites
* **Python 3.x**
* **PuTTY** (installed on your system).

### 2. Clone the Repository
`git clone https://github.com/lammilo/PCM`
`cd PCM`

### 3. Configuration
If PuTTY is not in the default path, open `manager.py` and update:
`PUTTY_PATH = r"C:\Your\Custom\Path\putty.exe"`

### 4. Run the Application
`python manager.py`

## 📖 Usage
* **New Server:** Click the `➕ Server` button.
* **Create Folder:** Use the `📁 New Folder` button.
* **Edit/Delete:** **Right-click** on any entry.
* **Import:** Use `📥 Import CSV`.
* **Move:** Drag a server and drop it onto a folder.

## 🛡️ Security Note
Connection data is stored unencrypted in `connections.db`. Do not upload this file to public repositories.

## 📄 License
This project is licensed under the MIT License.

---
