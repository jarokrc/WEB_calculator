import customtkinter as ctk
import tkinter as tk
from typing import Callable


class PdfContentDialog(ctk.CTkToplevel):
    """
    Editor textovych sekcii pre PDF (podla typu dokumentu).
    Umoznuje menit riadky pre sekcie: dodavatel, platba, klient.
    """

    def __init__(
        self,
        master,
        doc_type: str,
        data: dict,
        on_save: Callable[[dict], None],
        available_fields=None,
        firm_name: str = "",
    ):
        super().__init__(master)
        suffix = f" - {firm_name}" if firm_name else ""
        self.title(f"Nastavenia PDF - {doc_type}{suffix}")
        self.transient(master)
        self.grab_set()
        self.geometry("640x620")
        self.minsize(560, 520)
        self._on_save = on_save
        self._doc_type = doc_type
        self._fields = {}
        self._available_fields = available_fields or {}

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=12, pady=12)
        container.rowconfigure(2, weight=1)
        container.rowconfigure(4, weight=1)
        container.rowconfigure(6, weight=1)
        container.columnconfigure(0, weight=1)

        sections = [
            ("Dodavatel (riadky)", "supplier_lines"),
            ("Prehlad platby (riadky)", "payment_lines"),
            ("Odberatel (riadky)", "client_lines"),
            ("Suvaha (riadky)", "summary_lines"),
        ]
        row = 0
        for label, key in sections:
            ctk.CTkLabel(container, text=label, font=("Segoe UI", 11, "bold")).grid(row=row, column=0, sticky="w", pady=(4, 2))
            row += 1
            controls = ctk.CTkFrame(container, fg_color="transparent")
            controls.grid(row=row, column=0, sticky="ew")
            controls.columnconfigure(2, weight=1)
            box = ctk.CTkTextbox(container, height=120, wrap="word")
            box.grid(row=row + 1, column=0, sticky="nsew")
            container.rowconfigure(row + 1, weight=1)
            box.insert("1.0", "\n".join(data.get(key, [])))
            self._fields[key] = box

            options = self._available_fields.get(key, [])
            if options:
                import tkinter as tk

                var = tk.StringVar(value=options[0][0])
                combo = ctk.CTkComboBox(
                    controls,
                    values=[code for code, _label, _v in options],
                    variable=var,
                    state="readonly",
                    width=240,
                )
                combo.grid(row=0, column=0, sticky="w", padx=(0, 6))

                def insert_selected(box_ref, var_ref, opts):
                    code = var_ref.get()
                    val = ""
                    for c, lbl, v in opts:
                        if c == code:
                            # combine label + value without colon if both
                            if lbl and v:
                                val = f"{lbl} {v}"
                            else:
                                val = v or lbl
                            break
                    if val:
                        prefix = "" if (box_ref.get("1.0", "end").strip() == "") else "\n"
                        box_ref.insert("end", prefix + val)

                ctk.CTkButton(
                    controls,
                    text="Vlozit",
                    width=80,
                    command=lambda b=box, v=var, opts=options: insert_selected(b, v, opts),
                ).grid(row=0, column=1, sticky="w")
            row += 2

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.grid(row=row, column=0, sticky="e", pady=(10, 0))
        ctk.CTkButton(btns, text="Zrusit", command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btns, text="Ulozit", command=self._handle_save).pack(side="right")

    def _handle_save(self) -> None:
        result: dict[str, list[str]] = {}
        for key, widget in self._fields.items():
            raw = widget.get("1.0", "end").splitlines()
            lines = [line for line in (l.strip() for l in raw) if line]
            result[key] = lines
        self._on_save(result)
        self.destroy()
