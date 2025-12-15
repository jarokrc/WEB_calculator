import tkinter as tk
from tkinter import ttk
from typing import Iterable, Set


class FilterDialog(tk.Toplevel):
    """
    Simple modal dialog that lets the user select tags and sources.
    """

    def __init__(self, master: tk.Misc, tags: Iterable[str], sources: Iterable[str], selected_tags: Set[str], selected_sources: Set[str], on_apply):
        super().__init__(master)
        self.title("Filter")
        self.transient(master)
        self.grab_set()
        self.minsize(420, 320)
        self.resizable(True, True)
        self._on_apply = on_apply
        self._tags = sorted({t for t in tags if t})
        self._sources = sorted({s for s in sources if s})

        ttk.Label(self, text="Tagy").grid(row=0, column=0, sticky="w", padx=6, pady=(8, 2))
        self._tag_list = tk.Listbox(self, selectmode="multiple", height=min(10, len(self._tags)))
        for tag in self._tags:
            self._tag_list.insert(tk.END, tag)
        for idx, tag in enumerate(self._tags):
            if tag in selected_tags:
                self._tag_list.selection_set(idx)
        self._tag_list.grid(row=1, column=0, sticky="nsew", padx=6)

        ttk.Label(self, text="Zdroj").grid(row=0, column=1, sticky="w", padx=6, pady=(8, 2))
        self._src_list = tk.Listbox(self, selectmode="multiple", height=min(10, len(self._sources)))
        for src in self._sources:
            self._src_list.insert(tk.END, src)
        for idx, src in enumerate(self._sources):
            if src in selected_sources:
                self._src_list.selection_set(idx)
        self._src_list.grid(row=1, column=1, sticky="nsew", padx=6)

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", padx=6, pady=8)
        ttk.Button(btns, text="Zrušiť", command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(btns, text="Použiť", command=self._apply).pack(side="right")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def _apply(self) -> None:
        sel_tags = {self._tags[i] for i in self._tag_list.curselection()}
        sel_sources = {self._sources[i] for i in self._src_list.curselection()}
        self._on_apply(sel_tags, sel_sources)
        self.destroy()
