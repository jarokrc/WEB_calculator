import tkinter as tk
import customtkinter as ctk
from typing import Callable


class SupplierDialog(ctk.CTkToplevel):
    """
    Dialog na upravu firemnych udajov s profilmi (viac firiem) a polami s code/label/value.
    """

    def __init__(self, master, data: dict, on_save: Callable[[dict], None], firm_name: str = ""):
        super().__init__(master)
        suffix = f" - {firm_name}" if firm_name else ""
        self.title(f"Firemne udaje{suffix}")
        self.transient(master)
        self.grab_set()
        self.geometry("720x560")
        self.minsize(640, 480)
        self._on_save = on_save
        self._profiles = list(data.get("profiles", []))
        self._active = data.get("active") or (self._profiles[0]["id"] if self._profiles else "default")
        self._sources = list(data.get("sources", []))
        if not self._profiles:
            self._profiles = [{"id": "default", "name": "Default", "fields": []}]
        if not self._sources:
            self._sources = [{"code": "name", "label": "Nazov"}, {"code": "address", "label": "Adresa"}]
        self._normalize_sources()

        self._rows: list[tuple[tk.StringVar, tk.StringVar, tk.StringVar, ctk.CTkFrame]] = []
        self._code_combos: list[ctk.CTkComboBox] = []

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text="Firemne udaje", font=("Segoe UI", 13, "bold")).pack(side="left")

        combo_frame = ctk.CTkFrame(header, fg_color="transparent")
        combo_frame.pack(side="right")
        self._profile_var = tk.StringVar(value=self._profile_name(self._active))
        self._profile_box = ctk.CTkComboBox(
            combo_frame,
            values=self._profile_names(),
            variable=self._profile_var,
            state="readonly",
            width=160,
            command=lambda val: self._switch_profile_by_name(val),
        )
        self._profile_box.pack(side="left", padx=(0, 6))
        ctk.CTkButton(combo_frame, text="Nova firma", command=self._add_profile).pack(side="left")
        ctk.CTkButton(combo_frame, text="Premenovat", command=self._rename_profile).pack(side="left", padx=(6, 0))
        ctk.CTkButton(combo_frame, text="Zmaz profil", command=self._remove_profile).pack(side="left", padx=(6, 0))

        ctk.CTkButton(header, text="Pridat pole", command=self._add_row).pack(side="right", padx=(0, 12))

        self._body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=12, pady=6)
        self._body.rowconfigure(0, weight=1)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=12, pady=(6, 12))
        ctk.CTkButton(buttons, text="Zrusit", command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Ulozit", command=self._handle_save).pack(side="right")

        # Sources manager
        sources_frame = ctk.CTkFrame(self, fg_color="transparent")
        sources_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(sources_frame, text="Zdroje (code sablony)", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        list_frame = ctk.CTkFrame(sources_frame, fg_color="transparent")
        list_frame.pack(fill="x", pady=4)
        self._source_var = tk.StringVar(value=self._sources[0]["code"] if self._sources else "")
        self._source_list = ctk.CTkComboBox(
            list_frame,
            values=[s["code"] for s in self._sources],
            variable=self._source_var,
            state="readonly" if self._sources else "normal",
            width=200,
        )
        self._source_list.pack(side="left", padx=(0, 6))
        ctk.CTkButton(list_frame, text="Pridat zdroj", command=self._add_source).pack(side="left", padx=(0, 4))
        ctk.CTkButton(list_frame, text="Upravit", command=self._edit_source).pack(side="left", padx=4)
        ctk.CTkButton(list_frame, text="Zmaz", command=self._remove_source).pack(side="left", padx=4)

        self._load_profile(self._active)
        if not self._sources:
            import tkinter.messagebox as mb
            mb.showinfo("Chyba", "Najprv pridaj aspon jeden zdroj (code), aby si ho mohol pouzit pri poliach.", parent=self)

    def _current_profile(self) -> dict:
        for p in self._profiles:
            if p["id"] == self._active:
                return p
        return self._profiles[0]

    def _profile_names(self) -> list[str]:
        return [self._profile_name(p["id"]) for p in self._profiles]

    def _profile_name(self, profile_id: str) -> str:
        prof = next((p for p in self._profiles if p["id"] == profile_id), None)
        return prof.get("name") or prof.get("id") if prof else profile_id

    def _switch_profile_by_name(self, name: str) -> None:
        prof = next((p for p in self._profiles if (p.get("name") or p.get("id")) == name), None)
        if not prof:
            return
        self._switch_profile(prof["id"])

    def _switch_profile(self, profile_id: str) -> None:
        self._save_rows_to_profile()
        self._active = profile_id
        self._profile_var.set(self._profile_name(profile_id))
        self._clear_rows()
        self._load_profile(profile_id)

    def _add_profile(self) -> None:
        self._save_rows_to_profile()
        import tkinter.simpledialog as sd

        new_id = f"firma_{len(self._profiles)+1}"
        name = sd.askstring("Nova firma", "Nazov firmy:", initialvalue=new_id, parent=self)
        if name:
            new_id = name.strip().replace(" ", "_") or new_id
        self._profiles.append({"id": new_id, "name": name or new_id, "fields": []})
        self._profile_box.configure(values=self._profile_names())
        self._switch_profile(new_id)

    def _rename_profile(self) -> None:
        import tkinter.simpledialog as sd

        prof = self._current_profile()
        name = sd.askstring("Premenovat firmu", "Novy nazov firmy:", initialvalue=prof.get("name", prof.get("id")), parent=self)
        if name:
            prof["name"] = name.strip() or prof.get("name", prof.get("id"))
            self._profile_box.configure(values=self._profile_names())
            self._profile_var.set(self._profile_name(self._active))

    def _remove_profile(self) -> None:
        if len(self._profiles) <= 1:
            return
        self._profiles = [p for p in self._profiles if p["id"] != self._active]
        self._active = self._profiles[0]["id"]
        self._profile_box.configure(values=self._profile_names())
        self._profile_var.set(self._profile_name(self._active))
        self._clear_rows()
        self._load_profile(self._active)

    def _clear_rows(self) -> None:
        for _c, _l, _v, frame in list(self._rows):
            frame.destroy()
        self._rows.clear()
        self._code_combos.clear()

    def _load_profile(self, profile_id: str) -> None:
        prof = next((p for p in self._profiles if p["id"] == profile_id), self._profiles[0])
        for item in prof.get("fields", []):
            self._add_row(item.get("code", ""), item.get("value", ""), item.get("label", ""))

    def _save_rows_to_profile(self) -> None:
        prof = self._current_profile()
        fields: list[dict] = []
        for code_var, label_var, val_var, _f in self._rows:
            code = (code_var.get() or "").strip()
            label = (label_var.get() or "").strip()
            val = (val_var.get() or "").strip()
            if not code and not val and not label:
                continue
            fields.append({"code": code, "label": label, "value": val})
        prof["fields"] = fields

    def _add_row(self, code: str = "", value: str = "", label: str = "") -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", pady=4)
        code_var = tk.StringVar(value=code)
        label_var = tk.StringVar(value=label)
        val_var = tk.StringVar(value=value)
        combo = ctk.CTkComboBox(frame, values=[s["code"] for s in self._sources], variable=code_var, width=140, state="normal")
        combo.pack(side="left", padx=(0, 6))
        self._code_combos.append(combo)
        ctk.CTkEntry(frame, textvariable=label_var, width=160, placeholder_text="label (volitelne)").pack(side="left", padx=(0, 6))
        ctk.CTkEntry(frame, textvariable=val_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(frame, text="Odstranit", width=90, command=lambda f=frame: self._remove_row(f)).pack(side="left")
        self._rows.append((code_var, label_var, val_var, frame))

    def _remove_row(self, frame: ctk.CTkFrame) -> None:
        for idx, (_c, _l, _v, f) in enumerate(list(self._rows)):
            if f is frame:
                self._rows.pop(idx)
                f.destroy()
                break
        self._code_combos = [c for c in self._code_combos if c.winfo_exists()]

    def _handle_save(self) -> None:
        self._save_rows_to_profile()
        payload = {"active": self._active, "profiles": self._profiles, "sources": self._sources}
        self._on_save(payload)
        self.destroy()

    def _normalize_sources(self) -> None:
        seen = set()
        norm = []
        for src in self._sources:
            code = (src.get("code") or "").strip()
            label = (src.get("label") or code).strip()
            if not code and not label:
                continue
            key = code or label
            if key in seen:
                continue
            seen.add(key)
            norm.append({"code": code or label, "label": label or code})
        self._sources = norm

    def _refresh_source_widgets(self) -> None:
        self._normalize_sources()
        values = [s["code"] for s in self._sources] or [""]
        if hasattr(self, "_source_list"):
            self._source_list.configure(values=values)
            if values:
                self._source_var.set(values[0])
        for combo in list(self._code_combos):
            try:
                combo.configure(values=values)
            except Exception:
                continue

    def _add_source(self) -> None:
        import tkinter.simpledialog as sd
        code = sd.askstring("Novy zdroj", "Code:", parent=self)
        if not code:
            return
        label = sd.askstring("Label", "Popis (volitelne):", parent=self) or ""
        self._sources.append({"code": code.strip(), "label": label.strip()})
        self._refresh_source_widgets()

    def _edit_source(self) -> None:
        if not self._sources:
            return
        import tkinter.simpledialog as sd
        current = self._source_var.get()
        src = next((s for s in self._sources if s["code"] == current), None)
        if not src:
            return
        new_code = sd.askstring("Upravit zdroj", "Code:", initialvalue=src["code"], parent=self) or src["code"]
        new_label = sd.askstring("Label", "Popis (volitelne):", initialvalue=src.get("label", ""), parent=self) or src.get("label", "")
        src["code"] = new_code.strip()
        src["label"] = new_label.strip()
        self._refresh_source_widgets()

    def _remove_source(self) -> None:
        if not self._sources:
            return
        current = self._source_var.get()
        self._sources = [s for s in self._sources if s["code"] != current]
        if not self._sources:
            self._sources = [{"code": "code1", "label": "code1"}]
        self._refresh_source_widgets()
