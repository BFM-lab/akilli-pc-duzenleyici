import customtkinter as ctk
from config import LOGS_DIR
from ui.main_window import MainWindow


def main():
    # Log klasörü yoksa oluştur
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()