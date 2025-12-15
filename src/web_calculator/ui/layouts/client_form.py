import tkinter as tk
from tkinter import ttk


class ClientForm(ttk.LabelFrame):
    """
    Klientsky formulár s prepínaním súkromná osoba / firma.
    Ukladá hodnoty do vlastných StringVar premenných.
    """

    def __init__(self, master: tk.Misc, on_change, row: int = 0):
        super().__init__(master, text="Klient", padding=8)
        self.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8)
        for i in range(4):
            self.columnconfigure(i, weight=1)

        self.type = tk.StringVar(value="sukromna")
        self.name = tk.StringVar()
        self.company = tk.StringVar()
        self.ico = tk.StringVar()
        self.dic = tk.StringVar()
        self.icdph = tk.StringVar()
        self.email = tk.StringVar()
        self.address = tk.StringVar()
        self.name_label = tk.StringVar(value="Meno a priezvisko")

        self._on_change = on_change
        for var in (self.type, self.name, self.company, self.ico, self.dic, self.icdph, self.email, self.address):
            var.trace_add("write", lambda *_: self._on_change())

        ttk.Label(self, text="Typ").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(self, text="Sukromna osoba", variable=self.type, value="sukromna", command=self._update_type).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self, text="Firma", variable=self.type, value="firma", command=self._update_type).grid(row=0, column=2, sticky="w")

        ttk.Label(self, textvariable=self.name_label).grid(row=1, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.name).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(4, 0))

        self._ico_label = ttk.Label(self, text="ICO")
        self._ico_label.grid(row=2, column=0, sticky="w")
        self._ico_entry = ttk.Entry(self, textvariable=self.ico, width=16)
        self._ico_entry.grid(row=2, column=1, sticky="ew", padx=(4, 0))

        self._dic_label = ttk.Label(self, text="DIC")
        self._dic_label.grid(row=2, column=2, sticky="w")
        self._dic_entry = ttk.Entry(self, textvariable=self.dic, width=16)
        self._dic_entry.grid(row=2, column=3, sticky="ew", padx=(4, 0))

        self._icdph_label = ttk.Label(self, text="IC DPH")
        self._icdph_label.grid(row=3, column=0, sticky="w")
        self._icdph_entry = ttk.Entry(self, textvariable=self.icdph, width=16)
        self._icdph_entry.grid(row=3, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(self, text="Email").grid(row=4, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.email).grid(row=4, column=1, columnspan=3, sticky="ew", padx=(4, 0))

        ttk.Label(self, text="Adresa").grid(row=5, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.address).grid(row=5, column=1, columnspan=3, sticky="ew", padx=(4, 0))

        self._update_type()

    def _update_type(self) -> None:
        is_firm = self.type.get() == "firma"
        self.name_label.set("Spolocnost" if is_firm else "Meno a priezvisko")
        state = "normal" if is_firm else "disabled"
        for entry in (self._ico_entry, self._dic_entry, self._icdph_entry):
            entry.config(state=state)
        for widget in (self._ico_label, self._ico_entry, self._dic_label, self._dic_entry, self._icdph_label, self._icdph_entry):
            if is_firm:
                widget.grid()
            else:
                widget.grid_remove()
        if not is_firm:
            self.ico.set("")
            self.dic.set("")
            self.icdph.set("")
        self._on_change()

    def data(self) -> dict:
        return {
            "type": self.type.get(),
            "name": self.name.get(),
            "company": self.company.get(),
            "ico": self.ico.get(),
            "dic": self.dic.get(),
            "icdph": self.icdph.get(),
            "email": self.email.get(),
            "address": self.address.get(),
        }

    def set_data(self, data: dict) -> None:
        self.type.set(data.get("type", "sukromna"))
        self.name.set(data.get("name", ""))
        self.company.set(data.get("company", ""))
        self.ico.set(data.get("ico", ""))
        self.dic.set(data.get("dic", ""))
        self.icdph.set(data.get("icdph", ""))
        self.email.set(data.get("email", ""))
        self.address.set(data.get("address", ""))
        self._update_type()

    def reset(self) -> None:
        self.type.set("sukromna")
        self.name.set("")
        self.company.set("")
        self.ico.set("")
        self.dic.set("")
        self.icdph.set("")
        self.email.set("")
        self.address.set("")
        self._update_type()

    def has_data(self) -> bool:
        keys = ["name", "company", "ico", "dic", "icdph", "email", "address"]
        return any((self.data().get(k) or "").strip() for k in keys)
