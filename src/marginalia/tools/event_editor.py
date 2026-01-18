import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import marginalia.runtime
import marginalia.reflection as reflection


# ============================================================
# File location (dev-mode, editable)
# ============================================================

RUNTIME_DIR = Path(marginalia.runtime.__file__).parent
EVENT_KINDS_PATH = RUNTIME_DIR / "event_kinds.json"


# ============================================================
# Editor App
# ============================================================

class EventEditor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Marginalia Event Kind Editor")
        self.geometry("900x600")

        self.event_kinds = {}
        self.current_kind = None
        self.last_text_widget = None
        
        self.level_var = tk.StringVar(value="info")
        self.err_var = tk.StringVar(value="none")
        self.tag_success_var = tk.BooleanVar(value=False)
        self.tag_fail_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._load()


    # ---------------- UI ----------------

    def _build_ui(self):
        # root grid
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ============================================================
        # Left: event kind list
        # ============================================================
        
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns")
        
        ttk.Label(left, text="Event Kinds").pack(anchor="w")

        self.kind_list = tk.Listbox(left, width=30)
        self.kind_list.pack(fill="y", expand=True)
        self.kind_list.bind("<<ListboxSelect>>", self._on_select_kind)

        ttk.Button(left, text="New", command=self._new_kind).pack(fill="x")
        ttk.Button(left, text="Delete", command=self._delete_kind).pack(fill="x")

        # ============================================================
        # Right: split into form + token browser
        # ============================================================

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=3)   # form
        right.columnconfigure(1, weight=2)   # token browser
        right.rowconfigure(0, weight=1)

        # ---------------- Form ----------------

        form = ttk.Frame(right)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        form.columnconfigure(1, weight=1)

        row = 0

        def add(label):
            nonlocal row
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w")
            row += 1

        def add_entry():
            nonlocal row
            e = ttk.Entry(form)
            e.grid(row=row, column=1, sticky="ew")
            row += 1
            return e

        def add_text(height=4):
            nonlocal row
            t = tk.Text(form, height=height)
            t.grid(row=row, column=1, sticky="nsew")
            row += 1
            return t

        add("kind")
        self.kind_entry = add_entry()

        add("level")
        level_frame = ttk.Frame(form)
        level_frame.grid(row=row, column=1, sticky="w")
        row += 1
        
        for txt in ("info", "warning", "error"):
            rb = ttk.Radiobutton(
                level_frame,
                text=txt,
                value=txt,
                variable=self.level_var,
            )
            rb.pack(side="left", padx=4)

        add("err")

        err_frame = ttk.Frame(form)
        err_frame.grid(row=row, column=1, sticky="w")
        row += 1

        for txt in ("none", "usage", "schema", "io", "internal"):
            rb = ttk.Radiobutton(
                err_frame,
                text=txt,
                value=txt,
                variable=self.err_var,
            )
            rb.pack(side="left", padx=4)

        add("tags")

        tags_frame = ttk.Frame(form)
        tags_frame.grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Checkbutton(
            tags_frame,
            text="success",
            variable=self.tag_success_var,
        ).pack(side="left", padx=6)

        ttk.Checkbutton(
            tags_frame,
            text="fail",
            variable=self.tag_fail_var,
        ).pack(side="left", padx=6)


        add("msg-template")
        self.msg_text = add_text(5)
        self.msg_text.bind("<FocusIn>", self._remember_text_focus)

        add("data-template (JSON)")
        self.data_text = add_text(8)
        self.data_text.bind("<FocusIn>", self._remember_text_focus)

        ttk.Button(form, text="Save", command=self._save_current).grid(
            row=row, column=1, sticky="e", pady=6
        )

        # ---------------- Token Browser ----------------

        token_frame = ttk.LabelFrame(right, text="Insert Token")
        token_frame.grid(row=0, column=1, sticky="nsew")

        token_frame.columnconfigure(0, weight=1)
        token_frame.rowconfigure(0, weight=1)

        nb = ttk.Notebook(token_frame)
        nb.grid(row=0, column=0, sticky="nsew")

        self.token_notebook = nb
        self.token_trees = {}

        def make_tab(cat_name, items):
            frame = ttk.Frame(nb)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)

            tree = ttk.Treeview(
                frame,
                columns=("desc",),
                show="tree headings",
                selectmode="browse",
            )
            tree.heading("#0", text="Name")
            tree.heading("desc", text="Description")

            yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=yscroll.set)

            tree.grid(row=0, column=0, sticky="nsew")
            yscroll.grid(row=0, column=1, sticky="ns")

            for k, v in items.items():
                tree.insert("", "end", iid=k, text=k, values=(v.get("desc", ""),))

            nb.add(frame, text=cat_name)
            self.token_trees[cat_name] = tree

        make_tab("g-vars", reflection.registry.get("g-vars", {}))
        make_tab("args", reflection.registry.get("args", {}))
        make_tab("named-functions", reflection.registry.get("named-functions", {}))

        insert_btn = ttk.Button(
            token_frame,
            text="Insert Selected Token",
            command=self._insert_selected_token,
        )
        insert_btn.grid(row=1, column=0, sticky="e", pady=6)


    def _remember_text_focus(self, evt):
        self.last_text_widget = evt.widget
    
    # ---------------- Load / Save ----------------

    def _load(self):
        if not EVENT_KINDS_PATH.exists():
            messagebox.showerror("Error", f"Missing {EVENT_KINDS_PATH}")
            self.destroy()
            return

        with open(EVENT_KINDS_PATH, "r", encoding="utf-8") as f:
            self.event_kinds = json.load(f)

        self.kind_list.delete(0, tk.END)
        for k in sorted(self.event_kinds):
            self.kind_list.insert(tk.END, k)


    def _save_all(self):
        with open(EVENT_KINDS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.event_kinds, f, indent=2, sort_keys=True)


    # ---------------- Selection ----------------

    def _on_select_kind(self, evt):
        if not self.kind_list.curselection():
            return

        i = self.kind_list.curselection()[0]
        kind = self.kind_list.get(i)

        self._load_kind(kind)


    def _load_kind(self, kind):
        self.current_kind = kind
        D = self.event_kinds[kind]

        self.kind_entry.delete(0, tk.END)
        self.kind_entry.insert(0, kind)

        self.level_var.set(D.get("level", "info"))

        self.err_var.set(D.get("err") or "none")

        tags = set(D.get("tags", []))
        self.tag_success_var.set("success" in tags)
        self.tag_fail_var.set("fail" in tags)

        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", D.get("msg-template", ""))

        self.data_text.delete("1.0", tk.END)
        self.data_text.insert("1.0", json.dumps(D.get("data-template", {}), indent=2))


    # ---------------- Editing ----------------

    def _save_current(self):
        if not self.current_kind:
            return

        new_kind = self.kind_entry.get().strip()

        tags = []
        if self.tag_success_var.get():
            tags.append("success")
        if self.tag_fail_var.get():
            tags.append("fail")

        try:
            data = json.loads(self.data_text.get("1.0", tk.END))
        except Exception as e:
            messagebox.showerror("JSON Error", str(e))
            return

        D = {
            "level": self.level_var.get(),
            "err": None if self.err_var.get() == "none" else self.err_var.get(),
            "tags": tags,
            "msg-template": self.msg_text.get("1.0", tk.END).rstrip(),
            "data-template": data,
        }

        if new_kind != self.current_kind:
            del self.event_kinds[self.current_kind]

        self.event_kinds[new_kind] = D
        self.current_kind = new_kind

        self._save_all()
        self._load()


    def _new_kind(self):
        base = "new-event"
        i = 1
        name = base
        while name in self.event_kinds:
            i += 1
            name = f"{base}-{i}"

        self.event_kinds[name] = {
            "level": "info",
            "err": None,
            "tags": [],
            "msg-template": "",
            "data-template": {},
        }

        self._save_all()
        self._load()


    def _delete_kind(self):
        if not self.current_kind:
            return

        if not messagebox.askyesno("Delete", f"Delete {self.current_kind}?"):
            return

        del self.event_kinds[self.current_kind]
        self.current_kind = None

        self._save_all()
        self._load()

    # ---------------- Token insertion ----------------

    def _insert_selected_token(self):
        tree = self._current_tree()
        if not tree:
            return

        sel = tree.selection()
        if not sel:
            return

        name = sel[0]
        tab = self._current_tab()

        if tab == "g-vars":
            token = f"{{g:{name}}}"
        elif tab == "args":
            token = f"{{args:{name}}}"
        elif tab == "named-functions":
            token = f"{{fn:{name}}}"
        else:
            return

        widget = self.last_text_widget
        if not widget:
            messagebox.showinfo("Insert", "Click in msg-template or data-template first.")
            return

        widget.insert(tk.INSERT, token)


    def _current_tab(self):
        nb = None
        for child in self.children.values():
            if isinstance(child, ttk.Notebook):
                nb = child
        # safer: track explicitly, but this works for now

        # better: store reference, but quick solution:
        return self._get_notebook_tab_text()


    def _get_notebook_tab_text(self):
        # brute-force find notebook
        def find(w):
            if isinstance(w, ttk.Notebook):
                return w
            for c in w.winfo_children():
                r = find(c)
                if r:
                    return r
            return None

        nb = find(self)
        if not nb:
            return None

        idx = nb.index(nb.select())
        return nb.tab(idx, "text")


    def _current_tree(self):
        tab = self._current_tab()
        if not tab:
            return None
        return self.token_trees.get(tab)


# ============================================================
# Entry point
# ============================================================

def main():
    app = EventEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
