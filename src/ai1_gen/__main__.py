# src/ai1_gen/__main__.py
import sys

def main():
    # Eğer komut satırından --config gibi argümanlar verilmişse CLI'yi çalıştır
    if len(sys.argv) > 1:
        from ai1_gen.cli import main as cli_main
        cli_main()
    else:
        # Hiçbir argüman yoksa kullanıcı dostu GUI'yi başlat
        from ai1_gen.gui import AI1GenGUI
        app = AI1GenGUI()
        app.mainloop()

if __name__ == "__main__":
    main()