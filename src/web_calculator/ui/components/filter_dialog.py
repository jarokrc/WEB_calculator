import tkinter as tk
import customtkinter as ctk
from typing import Iterable, Set

from web_calculator.ui.styles import theme


class FilterDialog(ctk.CTkToplevel):
    """
    Modal dialog for tag/source filtering.
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

        ctk.CTkLabel(self, text="Tagy").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        self._tag_list = tk.Listbox(self, selectmode="multiple", height=min(10, len(self._tags)))
        theme.style_listbox(self._tag_list, theme.PALETTE)
        for tag in self._tags:
            self._tag_list.insert(tk.END, tag)
        for idx, tag in enumerate(self._tags):
            if tag in selected_tags:
                self._tag_list.selection_set(idx)
        self._tag_list.grid(row=1, column=0, sticky="nsew", padx=10)

        ctk.CTkLabel(self, text="Zdroj").grid(row=0, column=1, sticky="w", padx=10, pady=(10, 2))
        self._src_list = tk.Listbox(self, selectmode="multiple", height=min(10, len(self._sources)))
        theme.style_listbox(self._src_list, theme.PALETTE)
        for src in self._sources:
            self._src_list.insert(tk.END, src)
        for idx, src in enumerate(self._sources):
            if src in selected_sources:
                self._src_list.selection_set(idx)
        self._src_list.grid(row=1, column=1, sticky="nsew", padx=10)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btns, text="Zrusit", command=self.destroy).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btns, text="Pouzit", command=self._apply).pack(side="right")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def _apply(self) -> None:
        sel_tags = {self._tags[i] for i in self._tag_list.curselection()}
        sel_sources = {self._sources[i] for i in self._src_list.curselection()}
        self._on_apply(sel_tags, sel_sources)
        self.destroy()
