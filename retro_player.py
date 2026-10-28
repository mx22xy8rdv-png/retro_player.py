# language: Python, file: retro_player.py
# Зависимости: python-vlc
# Сборка: pyinstaller --noconsole --onefile --name RetroPlayer retro_player.py
# Для работы нужен установленный VLC media player (libvlc.dll).

import ctypes
import os
import random
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import vlc
    HAS_VLC = True
except ImportError:
    HAS_VLC = False

# ─── Цвета ──────────────────────────────────────────────────────────────────
BG_COLOR = "#7d4b73"
PANEL_COLOR = "#9c6b91"
BTN_COLOR = "#d4c5d2"
TEXT_COLOR = "#f0e6ef"
SLIDER_TROUGH = "#5a2e51"


# ─── DVD Логотип ────────────────────────────────────────────────────────────
class DVDLogo:
    """Летающий DVD-логотип: овал с градиентом и буквами DVD."""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.items = []
        self.running = False
        self.width = 160
        self.height = 70
        self.x = random.randint(50, 400)
        self.y = random.randint(50, 300)
        self.dx = random.choice([-4, -3, -2, 2, 3, 4])
        self.dy = random.choice([-4, -3, -2, 2, 3, 4])
        self._create_shape()

    def _create_shape(self):
        # Овал (основа логотипа)
        oval = self.canvas.create_oval(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill="#1a1a1a", outline="#ff3333", width=3, tags="dvd"
        )
        # Внутренний овал (градиент-эффект)
        inner = self.canvas.create_oval(
            self.x + 8, self.y + 8, self.x + self.width - 8, self.y + self.height - 8,
            fill="#222222", outline="#ff6666", width=1, tags="dvd"
        )
        # Текст DVD
        text = self.canvas.create_text(
            self.x + self.width // 2, self.y + self.height // 2,
            text="DVD", fill="#ff3333", font=("Impact", 32, "bold"), tags="dvd"
        )
        # Подпись VIDEO
        text2 = self.canvas.create_text(
            self.x + self.width // 2, self.y + self.height // 2 + 22,
            text="VIDEO", fill="#ff6666", font=("Arial", 10, "bold"), tags="dvd"
        )
        self.items = [oval, inner, text, text2]

    def start(self):
        self.running = True
        self._animate()

    def stop(self):
        self.running = False
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

    def _animate(self):
        if not self.running:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            self.canvas.after(50, self._animate)
            return

        self.x += self.dx
        self.y += self.dy
        bounced = False

        if self.x <= 10 or self.x + self.width >= w - 10:
            self.dx *= -1
            bounced = True
        if self.y <= 10 or self.y + self.height >= h - 10:
            self.dy *= -1
            bounced = True

        for item in self.items:
            self.canvas.move(item, self.dx if not bounced else 0, self.dy if not bounced else 0)
        # Если отскок — сдвигаем корректно
        if bounced:
            for item in self.items:
                self.canvas.coords(item, *self._get_coords(item))

        if bounced:
            self._change_color()

        self.canvas.after(20, self._animate)

    def _get_coords(self, item):
        # Пересчёт координат после отскока
        t = self.canvas.type(item)
        if t == "oval":
            return (self.x, self.y, self.x + self.width, self.y + self.height)
        elif t == "text":
            if self.canvas.itemcget(item, "text") == "DVD":
                return (self.x + self.width // 2, self.y + self.height // 2)
            else:
                return (self.x + self.width // 2, self.y + self.height // 2 + 22)
        return (0, 0)

    def _change_color(self):
        colors = ["#ff3333", "#33ff33", "#3333ff", "#ffff33", "#ff33ff", "#33ffff"]
        c = random.choice(colors)
        for item in self.items:
            self.canvas.itemconfig(item, fill=c)


# ─── Главное окно ───────────────────────────────────────────────────────────
class RetroPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")
        self.root.geometry("900x600")
        self.root.configure(bg=PANEL_COLOR)
        self.root.minsize(600, 400)

        if not HAS_VLC:
            messagebox.showerror("Ошибка", "python-vlc не установлен.\n\n"
                                            "Установи VLC media player и pip install python-vlc")
            sys.exit(1)

        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        self.media = None
        self.is_playing = False
        self.slider_dragging = False

        self._build_ui()

        # DVD-логотип запускается СРАЗУ, даже без видео
        self.dvd_logo = DVDLogo(self.video_panel)
        self.dvd_logo.start()

    def _build_ui(self):
        menubar = tk.Menu(self.root, bg=PANEL_COLOR, fg=TEXT_COLOR,
                          activebackground=BTN_COLOR, activeforeground="black",
                          font=("Segoe UI", 10))
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open File...", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle DVD Logo", command=self.toggle_dvd)
        menubar.add_cascade(label="View", menu=view_menu)
        play_menu = tk.Menu(menubar, tearoff=0)
        play_menu.add_command(label="Play", command=self.play)
        play_menu.add_command(label="Pause", command=self.pause)
        play_menu.add_command(label="Stop", command=self.stop)
        menubar.add_cascade(label="Play", menu=play_menu)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Options...", command=lambda: messagebox.showinfo("Options", "Not implemented yet."))
        menubar.add_cascade(label="Tools", menu=tools_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Retro Video Player\nPython + VLC"))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

        self.video_panel = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.video_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        self.root.update()
        self._embed_vlc()

        controls = tk.Frame(self.root, bg=PANEL_COLOR)
        controls.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.seek_slider = tk.Scale(controls, from_=0, to=100, orient=tk.HORIZONTAL,
                                    showvalue=0, bg=PANEL_COLOR, fg=TEXT_COLOR,
                                    troughcolor=SLIDER_TROUGH, highlightthickness=0,
                                    command=self._on_seek)
        self.seek_slider.pack(fill=tk.X, pady=(0, 5))
        self.seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, 'slider_dragging', True))
        self.seek_slider.bind("<ButtonRelease-1>", lambda e: setattr(self, 'slider_dragging', False))

        btn_frame = tk.Frame(controls, bg=PANEL_COLOR)
        btn_frame.pack(fill=tk.X)

        self.btn_play = tk.Button(btn_frame, text="▶", command=self.toggle_play,
                                  bg=BTN_COLOR, fg="black", font=("Segoe UI", 14, "bold"),
                                  bd=0, width=3, relief=tk.FLAT)
        self.btn_play.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(btn_frame, text="■", command=self.stop,
                  bg=BTN_COLOR, fg="black", font=("Segoe UI", 14),
                  bd=0, width=3, relief=tk.FLAT).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="|◀", command=self.prev,
                  bg=BTN_COLOR, fg="black", font=("Segoe UI", 12),
                  bd=0, width=3, relief=tk.FLAT).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="▶|", command=self.next,
                  bg=BTN_COLOR, fg="black", font=("Segoe UI", 12),
                  bd=0, width=3, relief=tk.FLAT).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(btn_frame, text="🔊", bg=PANEL_COLOR, fg=TEXT_COLOR,
                 font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=(10, 0))
        self.volume_slider = tk.Scale(btn_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                      showvalue=0, bg=PANEL_COLOR, fg=TEXT_COLOR,
                                      troughcolor=SLIDER_TROUGH, highlightthickness=0,
                                      length=100, command=self._on_volume)
        self.volume_slider.set(80)
        self.volume_slider.pack(side=tk.LEFT, padx=(5, 0))
        self.player.audio_set_volume(80)

        self.time_label = tk.Label(btn_frame, text="00:00 / 00:00",
                                   bg=PANEL_COLOR, fg=TEXT_COLOR,
                                   font=("Consolas", 11))
        self.time_label.pack(side=tk.RIGHT, padx=10)

        self.status = tk.Label(self.root, text="Ready", bg=PANEL_COLOR, fg=TEXT_COLOR,
                               anchor="w", font=("Segoe UI", 10))
        self.status.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.root.after(500, self._update_ui)

    def _embed_vlc(self):
        hwnd = self.video_panel.winfo_id()
        # На Windows winfo_id — это HWND дочернего окна Tk, VLC нужно родительское окно
        # через GetParent, чтобы видео было ВНУТРИ Canvas, а не поверх всего.
        try:
            parent = ctypes.windll.user32.GetParent(hwnd)
            if parent:
                hwnd = parent
        except Exception:
            pass
        self.player.set_hwnd(hwnd)

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Video",
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv"), ("All Files", "*.*")]
        )
        if path:
            self._load_media(path)

    def _load_media(self, path):
        self.player.stop()
        self.media = self.instance.media_new(path)
        self.player.set_media(self.media)
        self.status.config(text=f"Loaded: {os.path.basename(path)}")
        self.root.title(f"Video Player — {os.path.basename(path)}")
        self.play()

    def play(self):
        if self.media:
            if self.player.get_state() == vlc.State.Paused:
                self.player.pause()
            else:
                self.player.play()
            self.is_playing = True
            self.btn_play.config(text="❚❚")
            self.status.config(text="Playing")

    def pause(self):
        self.player.pause()
        self.is_playing = False
        self.btn_play.config(text="▶")
        self.status.config(text="Paused")

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.player.stop()
        self.is_playing = False
        self.btn_play.config(text="▶")
        self.status.config(text="Stopped")
        self.seek_slider.set(0)
        self.time_label.config(text="00:00 / 00:00")

    def prev(self):
        self.player.set_time(0)

    def next(self):
        length = self.player.get_length()
        if length > 0:
            self.player.set_time(length - 1000)

    def toggle_dvd(self):
        if self.dvd_logo.running:
            self.dvd_logo.stop()
        else:
            self.dvd_logo = DVDLogo(self.video_panel)
            self.dvd_logo.start()

    def _on_seek(self, val):
        if self.slider_dragging:
            return
        length = self.player.get_length()
        if length > 0:
            new_time = int((float(val) / 100) * length)
            self.player.set_time(new_time)

    def _on_volume(self, val):
        self.player.audio_set_volume(int(val))

    def _update_ui(self):
        if self.media:
            length = self.player.get_length()
            current = self.player.get_time()
            if length > 0:
                percent = (current / length) * 100
                if not self.slider_dragging:
                    self.seek_slider.set(percent)
                cur_m = int(current // 60000)
                cur_s = int((current % 60000) // 1000)
                len_m = int(length // 60000)
                len_s = int((length % 60000) // 1000)
                self.time_label.config(text=f"{cur_m:02d}:{cur_s:02d} / {len_m:02d}:{len_s:02d}")
            if self.player.get_state() == vlc.State.Ended:
                self.is_playing = False
                self.btn_play.config(text="▶")
                self.status.config(text="Finished")
        self.root.after(500, self._update_ui)


def main():
    root = tk.Tk()
    app = RetroPlayer(root)

    def on_close():
        app.player.stop()
        if app.dvd_logo:
            app.dvd_logo.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
