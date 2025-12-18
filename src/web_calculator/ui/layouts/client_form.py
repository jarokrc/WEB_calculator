import tkinter as tk
import customtkinter as ctk

from web_calculator.ui.styles import theme


class ClientForm(ctk.CTkFrame):
    """
    Client form with private person / company toggle and bound StringVars.
    """

    def __init__(self, master: tk.Misc, on_change, row: int = 0):
        super().__init__(master, fg_color=theme.PALETTE["panel"], corner_radius=8)
        self.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
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

        title = ctk.CTkLabel(self, text="Klient", font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 4))
        self._title_label = title
        row_offset = 1

        self._type_label = ctk.CTkLabel(self, text="Typ")
        self._type_label.grid(row=0 + row_offset, column=0, sticky="w", padx=8)
        self._radio_person = ctk.CTkRadioButton(
            self, text="Sukromna osoba", variable=self.type, value="sukromna", command=self._update_type
        )
        self._radio_person.grid(row=0 + row_offset, column=1, sticky="w")
        self._radio_firm = ctk.CTkRadioButton(
            self, text="Firma", variable=self.type, value="firma", command=self._update_type
        )
        self._radio_firm.grid(row=0 + row_offset, column=2, sticky="w")

        self._name_label = ctk.CTkLabel(self, textvariable=self.name_label)
        self._name_label.grid(row=1 + row_offset, column=0, sticky="w", padx=8)
        self._name_entry = ctk.CTkEntry(self, textvariable=self.name)
        self._name_entry.grid(
            row=1 + row_offset, column=1, columnspan=3, sticky="ew", padx=(4, 8)
        )

        self._ico_label = ctk.CTkLabel(self, text="ICO")
        self._ico_label.grid(row=2 + row_offset, column=0, sticky="w", padx=8)
        self._ico_entry = ctk.CTkEntry(self, textvariable=self.ico, width=140)
        self._ico_entry.grid(row=2 + row_offset, column=1, sticky="ew", padx=(4, 8))

        self._dic_label = ctk.CTkLabel(self, text="DIC")
        self._dic_label.grid(row=2 + row_offset, column=2, sticky="w")
        self._dic_entry = ctk.CTkEntry(self, textvariable=self.dic, width=140)
        self._dic_entry.grid(row=2 + row_offset, column=3, sticky="ew", padx=(4, 8))

        self._icdph_label = ctk.CTkLabel(self, text="IC DPH")
        self._icdph_label.grid(row=3 + row_offset, column=0, sticky="w", padx=8)
        self._icdph_entry = ctk.CTkEntry(self, textvariable=self.icdph, width=140)
        self._icdph_entry.grid(row=3 + row_offset, column=1, sticky="ew", padx=(4, 8))

        self._email_label = ctk.CTkLabel(self, text="Email")
        self._email_label.grid(row=4 + row_offset, column=0, sticky="w", padx=8)
        self._email_entry = ctk.CTkEntry(self, textvariable=self.email)
        self._email_entry.grid(
            row=4 + row_offset, column=1, columnspan=3, sticky="ew", padx=(4, 8)
        )

        self._address_label = ctk.CTkLabel(self, text="Adresa")
        self._address_label.grid(row=5 + row_offset, column=0, sticky="w", padx=8)
        self._address_entry = ctk.CTkEntry(self, textvariable=self.address)
        self._address_entry.grid(
            row=5 + row_offset, column=1, columnspan=3, sticky="ew", padx=(4, 8), pady=(0, 8)
        )

        self._labels = [
            self._title_label,
            self._type_label,
            self._name_label,
            self._ico_label,
            self._dic_label,
            self._icdph_label,
            self._email_label,
            self._address_label,
        ]
        self._entries = [
            self._name_entry,
            self._ico_entry,
            self._dic_entry,
            self._icdph_entry,
            self._email_entry,
            self._address_entry,
        ]
        self._radios = [self._radio_person, self._radio_firm]

        self._update_type()
        self.update_theme(theme.PALETTE)

    def update_theme(self, palette: dict) -> None:
        self.configure(fg_color=palette["panel"])
        for label in self._labels:
            label.configure(text_color=palette["text"])
        for entry in self._entries:
            entry.configure(
                fg_color=palette["surface"],
                border_color=palette["border"],
                text_color=palette["text"],
            )
        for radio in self._radios:
            radio.configure(text_color=palette["text"], fg_color=palette["accent"])

    def _update_type(self) -> None:
        is_firm = self.type.get() == "firma"
        self.name_label.set("Spolocnost" if is_firm else "Meno a priezvisko")
        state = "normal" if is_firm else "disabled"
        for entry in (self._ico_entry, self._dic_entry, self._icdph_entry):
            entry.configure(state=state)
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
