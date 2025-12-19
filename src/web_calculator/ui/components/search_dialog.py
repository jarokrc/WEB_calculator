import tkinter as tk
import customtkinter as ctk
from typing import Iterable

from web_calculator.core.models.service import Service
from web_calculator.ui.styles import theme


class SearchDialog(ctk.CTkToplevel):
    def __init__(self, master: tk.Misc, services: Iterable[Service], on_select_code, firm_name: str = ""):
        super().__init__(master)
        suffix = f" - {firm_name}" if firm_name else ""
        self.title(f"Vyhladavanie sluzieb{suffix}")
        self.transient(master)
        self.grab_set()
        self.minsize(520, 400)
        self.resizable(True, True)

        self._on_select_code = on_select_code
        self._services = list(services)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text="Hladat").pack(anchor="w")
        self._query = tk.StringVar()
        entry = ctk.CTkEntry(frame, textvariable=self._query)
        entry.pack(fill="x", pady=(2, 8))
        entry.bind("<KeyRelease>", lambda _e: self._refresh())
        entry.focus_set()

        self._list = tk.Listbox(frame, height=20)
        theme.style_listbox(self._list, theme.PALETTE)
        self._list.pack(fill="both", expand=True)
        self._list.bind("<Double-Button-1>", self._choose)
        self._list.bind("<Return>", self._choose)
        self._list.bind("<KP_Enter>", self._choose)

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", pady=8)
        ctk.CTkButton(btns, text="Vybrat", command=self._choose).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btns, text="Zavriet", command=self.destroy).pack(side="right")

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
