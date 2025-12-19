import customtkinter as ctk


class PdfExportDialog(ctk.CTkToplevel):
    """
    Vyber PDF typu + moznost upravit texty sekcii.
    """

    def __init__(self, master, on_select, on_edit, firm_name: str = ""):
        super().__init__(master)
        suffix = f" - {firm_name}" if firm_name else ""
        self.title(f"Vyber typ PDF{suffix}")
        self.transient(master)
        self.grab_set()
        self.geometry("420x240")
        self.minsize(380, 220)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frame, text="Zvol dokument", font=("Segoe UI", 12, "bold")).pack(pady=(0, 12))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", expand=True, pady=(0, 8))

        def choose(doc_type: str) -> None:
            try:
                on_select(doc_type)
            finally:
                self.destroy()

        def edit(doc_type: str) -> None:
            on_edit(doc_type)

        for text, dtype in (("Cenova ponuka", "quote"), ("Predfaktura", "proforma"), ("Faktura", "invoice")):
            row = ctk.CTkFrame(btns, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkButton(row, text=text, command=lambda d=dtype: choose(d)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(row, text="Upravit texty", command=lambda d=dtype: edit(d), width=120).pack(side="left")

        ctk.CTkButton(frame, text="Zrusit", command=self.destroy).pack(pady=(12, 0))
