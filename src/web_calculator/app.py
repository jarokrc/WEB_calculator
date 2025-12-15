from web_calculator.core.services.catalog import load_catalog
from web_calculator.ui.layouts.main_window import MainWindow


def main() -> None:
    catalog = load_catalog()
    app = MainWindow(catalog)
    app.mainloop()


if __name__ == "__main__":
    main()
