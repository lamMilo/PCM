import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import subprocess
import sqlite3
from pathlib import Path
import csv

# ===== CONFIG =====
PUTTY_PATH = r"C:\Program Files\PuTTY\putty.exe"
APP_DIR = Path(__file__).parent
DB_FILE = APP_DIR / "connections.db"

class PuttyManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PuTTY Manager Pro")
        self.geometry("600x700")

        # Theme Status
        self.dark_mode = False
        self.style = ttk.Style(self)

        # ===== SEARCH =====
        self.search_var = tk.StringVar()
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=6, pady=6)
        
        search = ttk.Entry(search_frame, textvariable=self.search_var)
        search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search.insert(0, "Search...")
        search.bind("<FocusIn>", self._clear_placeholder)
        search.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace_add("write", lambda *_: self.load_connections())

        # Theme Button
        self.theme_btn = ttk.Button(search_frame, text="🌓 Mode", command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT, padx=4)

        # ===== TREE =====
        self.tree = ttk.Treeview(self, columns=("host", "user"), show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6)
        
        # Scrollbar für Treeview
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<ButtonRelease-1>", self.on_drop)

        # ===== BUTTON BAR =====
        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=6)
        ttk.Button(btns, text="➕ New Connection", command=self.create_connection).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="📁 New Folder", command=self.add_new_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="📥 Import CSV", command=self.import_csv).pack(side=tk.LEFT, padx=4)

        # ===== MENUS =====
        self.server_menu = tk.Menu(self, tearoff=0)
        self.server_menu.add_command(label="✏️ Edit", command=self.edit_connection)
        self.server_menu.add_command(label="🗑 Delete", command=self.delete_connection)

        self.folder_menu = tk.Menu(self, tearoff=0)
        self.folder_menu.add_command(label="➕ Create New Connection Here", command=self.create_connection_in_folder)
        self.folder_menu.add_command(label="✏️ Rename Folder", command=self.rename_folder)
        self.folder_menu.add_command(label="🗑 Delete Folder", command=self.delete_folder)

        # ===== DB & STATE =====
        self.db = sqlite3.connect(DB_FILE)
        self.init_db()
        self.folder_nodes = {}
        self.server_nodes = {}
        self.drag_item = None
        self.known_folders = set()

        self.load_connections()
        self.apply_theme() # Initiales Theme

    def init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                host TEXT,
                user TEXT,
                folder TEXT
            )
        """)
        self.db.commit()

    # ===== THEME LOGIC =====
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.dark_mode:
            bg = "#2d2d2d"
            fg = "#ffffff"
            field_bg = "#3d3d3d"
            self.configure(bg=bg)
            self.style.theme_use('clam')
            self.style.configure("Treeview", background=field_bg, foreground=fg, fieldbackground=field_bg, bordercolor=bg)
            self.style.map("Treeview", background=[('selected', '#4a90e2')])
            self.style.configure("TFrame", background=bg)
            self.style.configure("TLabel", background=bg, foreground=fg)
            self.style.configure("TButton", padding=3)
        else:
            self.configure(bg="#f0f0f0")
            self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'default')
            self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
            self.style.map("Treeview", background=[('selected', '#3399ff')])

    # ===== FOLDER LOGIC =====
    def add_new_folder(self):
        new_folder = simpledialog.askstring("Neuer Ordner", "Name des Ordners:")
        if new_folder and new_folder not in self.known_folders:
            # Wir legen einen "Dummy"-Server an oder merken uns den Ordner einfach in der Liste
            # Da die UI auf DB-Einträgen basiert, laden wir ihn direkt in die bekannte Liste
            self.known_folders.add(new_folder)
            self.load_connections()

    # ===== CSV IMPORT (OBSERVIUM) =====
    def import_csv(self):
        path = filedialog.askopenfilename(title="Import Observium CSV", filetypes=[("CSV files", "*.csv")])
        if not path: return
        added = 0
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name, host = row.get("Device Name"), row.get("Management IP")
                if name and host:
                    self.db.execute("INSERT INTO servers (name, host, user, folder) VALUES (?, ?, ?, ?)",
                                   (name.strip(), host.strip(), "", "Observium"))
                    added += 1
        self.db.commit()
        self.load_connections()
        messagebox.showinfo("Erfolg", f"{added} Geräte importiert.")

    def _clear_placeholder(self, _):
        if self.search_var.get() == "Search...": self.search_var.set("")

    def _restore_placeholder(self, _):
        if not self.search_var.get(): self.search_var.set("Search...")

    # ===== LOAD TREE =====
    def load_connections(self):
        self.tree.delete(*self.tree.get_children())
        self.folder_nodes.clear()
        self.server_nodes.clear()

        q = self.search_var.get().lower()
        rows = self.db.execute("SELECT id,name,host,user,folder FROM servers").fetchall()
        
        # Sammle alle Ordner aus DB + manuell erstellte
        db_folders = set(r[4] for r in rows)
        all_folders = sorted(list(db_folders | self.known_folders))

        for folder in all_folders:
            if not folder: folder = "Default"
            fnode = self.tree.insert("", "end", text=f"📁 {folder}", open=True)
            self.folder_nodes[folder] = fnode

            servers = sorted([r for r in rows if r[4] == folder], key=lambda x: x[1].lower())
            for sid, name, host, user, _ in servers:
                if q and q != "search...":
                    if not (q in name.lower() or q in host.lower()): continue

                node = self.tree.insert(fnode, "end", text=f"  🖥 {name}", values=(host, user))
                self.server_nodes[node] = {"id": sid, "name": name, "host": host, "user": user, "folder": folder}

    # ===== CRUD OPERATIONS =====
    def create_connection(self):
        self._create_dialog("Default")

    def create_connection_in_folder(self):
        folder_text = self.tree.item(self.tree.focus(), "text").replace("📁 ", "")
        self._create_dialog(folder_text)

    def _create_dialog(self, folder):
        name = simpledialog.askstring("Server", "Name:")
        host = simpledialog.askstring("Host", "IP / Hostname:")
        if not name or not host: return
        user = simpledialog.askstring("User", "Username (optional):") or ""
        self.db.execute("INSERT INTO servers (name, host, user, folder) VALUES (?, ?, ?, ?)", (name, host, user, folder))
        self.db.commit()
        self.load_connections()

    def edit_connection(self):
        focus = self.tree.focus()
        if focus not in self.server_nodes: return
        s = self.server_nodes[focus]
        name = simpledialog.askstring("Edit", "Name:", initialvalue=s["name"])
        host = simpledialog.askstring("Edit", "Host:", initialvalue=s["host"])
        if not host: return
        user = simpledialog.askstring("Edit", "User:", initialvalue=s["user"]) or ""
        folder = simpledialog.askstring("Edit", "Folder:", initialvalue=s["folder"]) or s["folder"]

        self.db.execute("UPDATE servers SET name=?,host=?,user=?,folder=? WHERE id=?", (name, host, user, folder, s["id"]))
        self.db.commit()
        self.load_connections()

    def delete_connection(self):
        focus = self.tree.focus()
        if focus not in self.server_nodes: return
        s = self.server_nodes[focus]
        if messagebox.askyesno("Delete", f"Server '{s['name']}' löschen?"):
            self.db.execute("DELETE FROM servers WHERE id=?", (s["id"],))
            self.db.commit()
            self.load_connections()

    def delete_folder(self):
        folder = self.tree.item(self.tree.focus(), "text").replace("📁 ", "")
        if messagebox.askyesno("Delete Folder", f"Ordner '{folder}' und alle Inhalte löschen?"):
            self.db.execute("DELETE FROM servers WHERE folder=?", (folder,))
            self.db.commit()
            if folder in self.known_folders: self.known_folders.remove(folder)
            self.load_connections()

    def rename_folder(self):
        old = self.tree.item(self.tree.focus(), "text").replace("📁 ", "")
        new = simpledialog.askstring("Rename", "Neuer Name:", initialvalue=old)
        if new:
            self.db.execute("UPDATE servers SET folder=? WHERE folder=?", (new, old))
            self.db.commit()
            if old in self.known_folders:
                self.known_folders.remove(old)
                self.known_folders.add(new)
            self.load_connections()

    # ===== DRAG & DROP =====
    def on_drag_start(self, e):
        item = self.tree.identify_row(e.y)
        self.drag_item = item if item in self.server_nodes else None

    def on_drop(self, e):
        if not self.drag_item: return
        target = self.tree.identify_row(e.y)
        if target and target in self.folder_nodes.values():
            folder = self.tree.item(target, "text").replace("📁 ", "")
            sid = self.server_nodes[self.drag_item]["id"]
            self.db.execute("UPDATE servers SET folder=? WHERE id=?", (folder, sid))
            self.db.commit()
            self.load_connections()
        self.drag_item = None

    # ===== ACTION =====
    def on_double_click(self, _):
        item = self.tree.focus()
        if item in self.server_nodes:
            s = self.server_nodes[item]
            target = f"{s['user']}@{s['host']}" if s["user"] else s["host"]
            try:
                subprocess.Popen([PUTTY_PATH, "-ssh", target])
            except FileNotFoundError:
                messagebox.showerror("Error", f"PuTTY nicht gefunden unter: {PUTTY_PATH}")

    def on_right_click(self, e):
        item = self.tree.identify_row(e.y)
        if not item: return
        self.tree.selection_set(item)
        if item in self.server_nodes:
            self.server_menu.post(e.x_root, e.y_root)
        else:
            self.folder_menu.post(e.x_root, e.y_root)

if __name__ == "__main__":
    PuttyManager().mainloop()
