# src/ai1_gen/gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import concurrent.futures as cf
from pathlib import Path
import json

# Mevcut projeden gerekli fonksiyonları içe aktarıyoruz
from ai1_gen.config import load_config
from ai1_gen.io.exporter import ensure_dataset_dirs
from ai1_gen.cli import _worker_generate_validate_save, _split_of

class AI1GenGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI1-Gen: Sentetik Belge Üretici")
        self.geometry("650x550")
        self.resizable(False, False)

        # UI Güncellemeleri için kuyruk
        self.progress_queue = queue.Queue()
        
        self._build_ui()
        self._check_queue()

    def _build_ui(self):
        # Sekme Yöneticisi
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. SEKME: Varsayılan (Hızlı) Mod
        self.tab_default = ttk.Frame(notebook)
        notebook.add(self.tab_default, text="Hızlı / Varsayılan Mod")
        self._build_default_tab()

        # 2. SEKME: Özel Ayarlı Mod
        self.tab_custom = ttk.Frame(notebook)
        notebook.add(self.tab_custom, text="Özel Ayarlı Mod")
        self._build_custom_tab()

        # Alt Kısım: Çıktı Dizini, İlerleme Çubuğu ve Loglar
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Çıktı Dizini Seçimi
        out_frame = ttk.Frame(bottom_frame)
        out_frame.pack(fill=tk.X, pady=5)
        ttk.Label(out_frame, text="Çıktı Klasörü:").pack(side=tk.LEFT)
        self.out_path_var = tk.StringVar(value="D:/ai1_dataset_v1")
        ttk.Entry(out_frame, textvariable=self.out_path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(out_frame, text="Gözat...", command=self._browse_out_dir).pack(side=tk.LEFT)

        # Başlat Butonu
        self.btn_start = ttk.Button(bottom_frame, text="Üretimi Başlat", command=self._start_generation)
        self.btn_start.pack(pady=10)

        # İlerleme Çubuğu
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Durum Metni / Log
        self.status_var = tk.StringVar(value="Hazır.")
        ttk.Label(bottom_frame, textvariable=self.status_var, font=("Consolas", 9)).pack(anchor=tk.W)

    def _build_default_tab(self):
        frame = ttk.Frame(self.tab_default, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Bu mod, varsayılan yapılandırma (configs/default.yaml) dosyasını kullanarak\nrastgele belgeler üretir. Sadece sayfa sayısını belirlemeniz yeterlidir.", justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Üretilecek Sayfa Sayısı:").pack(side=tk.LEFT)
        self.def_pages_var = tk.IntVar(value=10)
        ttk.Entry(row1, textvariable=self.def_pages_var, width=10).pack(side=tk.LEFT, padx=10)

    def _build_custom_tab(self):
        frame = ttk.Frame(self.tab_custom, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Bu modda üretim parametrelerini özelleştirebilirsiniz.", justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

        # Config Seçimi
        row_cfg = ttk.Frame(frame)
        row_cfg.pack(fill=tk.X, pady=5)
        ttk.Label(row_cfg, text="Yapılandırma Dosyası:").pack(side=tk.LEFT)
        self.cfg_path_var = tk.StringVar(value="configs/default.yaml")
        ttk.Entry(row_cfg, textvariable=self.cfg_path_var, width=35).pack(side=tk.LEFT, padx=5)
        ttk.Button(row_cfg, text="Seç", command=self._browse_cfg).pack(side=tk.LEFT)

        # Sayfa Sayısı & İşçi (Worker) Sayısı
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=10)
        ttk.Label(row1, text="Sayfa Sayısı:").pack(side=tk.LEFT)
        self.cust_pages_var = tk.IntVar(value=100)
        ttk.Entry(row1, textvariable=self.cust_pages_var, width=8).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row1, text="Worker Sayısı:").pack(side=tk.LEFT)
        self.cust_workers_var = tk.IntVar(value=4)
        ttk.Entry(row1, textvariable=self.cust_workers_var, width=5).pack(side=tk.LEFT, padx=5)

        # Seed Belirleme
        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="Rastgelelik Tohumu (Seed):").pack(side=tk.LEFT)
        self.cust_seed_var = tk.IntVar(value=1337)
        ttk.Entry(row2, textvariable=self.cust_seed_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="(-1 rastgele bırakır)").pack(side=tk.LEFT)

    def _browse_out_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_path_var.set(d)

    def _browse_cfg(self):
        f = filedialog.askopenfilename(filetypes=[("YAML Files", "*.yaml *.yml")])
        if f:
            self.cfg_path_var.set(f)

    def _check_queue(self):
        """Arka plan iş parçacığından gelen mesajları UI'a yansıtır."""
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg["type"] == "progress":
                    self.progress_var.set(msg["pct"])
                    self.status_var.set(msg["text"])
                elif msg["type"] == "done":
                    self.btn_start.config(state=tk.NORMAL)
                    messagebox.showinfo("Tamamlandı", f"Üretim tamamlandı.\nToplam Başarılı: {msg['ok']}\nToplam Hata: {msg['fail']}")
                elif msg["type"] == "error":
                    self.btn_start.config(state=tk.NORMAL)
                    messagebox.showerror("Hata", msg["text"])
        except queue.Empty:
            pass
        finally:
            self.after(100, self._check_queue)

    def _start_generation(self):
        self.btn_start.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # Hangi sekmenin aktif olduğunu kontrol et
        current_tab = self.nametowidget(self.nametowidget(self.winfo_children()[0]).select()).winfo_name()
        
        if "default" in current_tab:
            pages = self.def_pages_var.get()
            workers = 4 # Varsayılan makul bir worker sayısı
            seed = 1337
            cfg_path = "configs/default.yaml"
        else:
            pages = self.cust_pages_var.get()
            workers = self.cust_workers_var.get()
            seed = self.cust_seed_var.get()
            cfg_path = self.cfg_path_var.get()

        out_dir = self.out_path_var.get()

        # Üretimi arka plan thread'inde başlat
        thread = threading.Thread(target=self._run_cli_logic, args=(cfg_path, out_dir, pages, workers, seed))
        thread.daemon = True
        thread.start()

    def _run_cli_logic(self, cfg_path, out_dir, total_pages, workers, seed):
        """cli.py içindeki ana mantığın arayüze uyarlanmış hali."""
        try:
            cfg = load_config(cfg_path)
            out_root = Path(out_dir)
            dirs = ensure_dataset_dirs(out_root)
            
            run_cfg = (cfg.raw.get("run", {}) or {}) if hasattr(cfg, "raw") else {}
            worker_options = {
                "max_tries": 4,
                "disable_augment_on_try": 2,
                "jitter_seed_step": 10_000_019,
                "fallback_dpi": 300,
            }

            dirs_str = {k: str(v) for k, v in dirs.items()}
            page_ids = [f"{i:06d}" for i in range(total_pages)]

            ok, fail = 0, 0
            produced_ids = []
            
            # cf.ProcessPoolExecutor ile asenkron işlem
            with cf.ProcessPoolExecutor(max_workers=workers) as ex:
                pending = set()
                fut_to_pid = {}
                
                it = iter(enumerate(page_ids))
                max_pending = max(int(2.0 * workers), 8)

                for _ in range(min(max_pending, total_pages)):
                    idx, pid = next(it)
                    fut = ex.submit(_worker_generate_validate_save, (idx, pid, seed, str(Path(cfg_path).resolve()), dirs_str, worker_options))
                    pending.add(fut)
                    fut_to_pid[fut] = pid

                done_count = 0
                while pending:
                    done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
                    for fut in done:
                        done_count += 1
                        res = fut.result()
                        if res.get("ok", False):
                            ok += 1
                            produced_ids.append(res.get("page_id"))
                        else:
                            fail += 1

                        # UI'a bilgi gönder
                        pct = (done_count / total_pages) * 100
                        self.progress_queue.put({
                            "type": "progress", 
                            "pct": pct, 
                            "text": f"Üretiliyor... ({done_count}/{total_pages}) | Başarılı: {ok} | Hatalı: {fail}"
                        })

                    # Yeni işleri ekle
                    for _ in range(len(done)):
                        try:
                            idx, pid = next(it)
                            nf = ex.submit(_worker_generate_validate_save, (idx, pid, seed, str(Path(cfg_path).resolve()), dirs_str, worker_options))
                            pending.add(nf)
                            fut_to_pid[nf] = pid
                        except StopIteration:
                            break

            # Tamamlandı mesajı
            self.progress_queue.put({"type": "done", "ok": ok, "fail": fail})

        except Exception as e:
            self.progress_queue.put({"type": "error", "text": str(e)})

if __name__ == "__main__":
    app = AI1GenGUI()
    app.mainloop()