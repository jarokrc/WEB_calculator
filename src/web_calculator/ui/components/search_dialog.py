import tkinter as tk
from tkinter import ttk
from typing import Iterable

from web_calculator.core.models.service import Service


class SearchDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, services: Iterable[Service], on_select_code):
        super().__init__(master)
        self.title("Vyhľadávanie služieb")
        self.transient(master)
        self.grab_set()
        self.minsize(520, 400)
        self.resizable(True, True)

        self._on_select_code = on_select_code
        self._services = list(services)

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Hľadaj").pack(anchor="w")
        self._query = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self._query)
        entry.pack(fill="x", pady=(2, 8))
        entry.bind("<KeyRelease>", lambda _e: self._refresh())
        entry.focus_set()

        self._list = tk.Listbox(frame, height=20)
        self._list.pack(fill="both", expand=True)
        self._list.bind("<Double-Button-1>", self._choose)
        self._list.bind("<Return>", self._choose)
        self._list.bind("<KP_Enter>", self._choose)

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Vybrať", command=self._choose).pack(side="right", padx=(4, 0))
        ttk.Button(btns, text="Zavrieť", command=self.destroy).pack(side="right")

        self._refresh()

    def _score(self, svc: Service, q: str) -> int:
        label = (svc.label or "").lower()
        code = (svc.code or "").lower()
        q = q.lower()
        if not q:
            return 0
        if label.startswith(q) or code.startswith(q):
            return 0
        idx = label.find(q)
        if idx == -1:
            idx = code.find(q)
        return idx if idx >= 0 else 999

    def _refresh(self) -> None:
        query = self._query.get().strip().lower()
        self._list.delete(0, tk.END)
        matches = []
        for svc in self._services:
            label = (svc.label or "").lower()
            code = (svc.code or "").lower()
            if query and query not in label and query not in code:
                continue
            matches.append((self._score(svc, query), svc))
        matches.sort(key=lambda t: (t[0], t[1].label))
        for _score, svc in matches[:200]:
            self._list.insert(tk.END, f"{svc.label} [{svc.code}]")
        if self._list.size():
            self._list.selection_set(0)

    def _choose(self, _event=None) -> None:
        sel = self._list.curselection()
        if not sel:
            return
        line = self._list.get(sel[0])
        code = line.rsplit("[", 1)[-1].rstrip("]") if "[" in line else line
        self._on_select_code(code.strip())
        self.destroy()
