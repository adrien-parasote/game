import contextlib
import os
import random
import threading

import customtkinter as ctk
from asset_creator.core.generator import generate_texture
from asset_creator.core.quantizer import quantize_image
from asset_creator.config.palette_loader import load_palettes
from asset_creator.exporters.exporter import export_tile
from PIL import Image

from asset_creator.core.constants import DEFAULT_TEXTURES, DEFAULT_PALETTES

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Asset Creator - Procedural")
        self.geometry("600x600")

        self.textures = DEFAULT_TEXTURES
        self.palettes = DEFAULT_PALETTES

        if os.path.exists("textures.json"):
            import json
            try:
                with open("textures.json", encoding="utf-8") as f:
                    self.textures = json.load(f)
            except Exception:
                pass

        # Try to load palettes from new location
        palette_path = os.path.join(os.path.dirname(__file__), "..", "config", "palettes.json")
        if os.path.exists(palette_path):
            with contextlib.suppress(Exception):
                self.palettes = load_palettes(palette_path)
        elif os.path.exists("palettes.json"):
            with contextlib.suppress(Exception):
                self.palettes = load_palettes("palettes.json")

        if not self.palettes:
            self.palettes = DEFAULT_PALETTES

        self.texture_var = ctk.StringVar(value=self.textures[0])
        self.palette_var = ctk.StringVar(value=next(iter(self.palettes.keys())))

        initial_seed = random.randint(0, 9999)
        self.seed_var = ctk.StringVar(value=str(initial_seed))
        self.density_var = ctk.StringVar(value="20")
        
        self.subtypes = ["Classic", "Short", "Curly", "Wild"]
        self.subtype_var = ctk.StringVar(value=self.subtypes[0])

        self.custom_palette = [(0,0,0), (85,85,85), (170,170,170), (255,255,255)]
        
        self._debounce_timer = None
        self.current_img_32 = None

        def on_seed_write(*args):
            try:
                self.seed_slider.set(int(self.seed_var.get()))
            except (ValueError, AttributeError):
                pass
            self.schedule_preview()

        def on_density_write(*args):
            try:
                self.density_slider.set(int(self.density_var.get()))
            except (ValueError, AttributeError):
                pass
            self.schedule_preview()

        def on_palette_write(*args):
            choice = self.palette_var.get()
            pal = self.palettes.get(choice, [(0,0,0),(85,85,85),(170,170,170),(255,255,255)])
            pal = sorted(pal, key=lambda c: 0.299*c[0] + 0.587*c[1] + 0.114*c[2])
            L = len(pal)
            self.custom_palette = [
                pal[0],
                pal[max(1, (L-1)//3)],
                pal[max(1, 2*(L-1)//3)],
                pal[L-1]
            ]
            for idx, color in enumerate(self.custom_palette):
                hex_color = "#%02x%02x%02x" % color
                self.custom_color_btns[idx].configure(fg_color=hex_color, hover_color=hex_color)
            self.schedule_preview()

        self.texture_var.trace_add("write", lambda *args: self.schedule_preview())
        self.subtype_var.trace_add("write", lambda *args: self.schedule_preview())
        self.palette_var.trace_add("write", on_palette_write)
        self.seed_var.trace_add("write", on_seed_write)
        self.density_var.trace_add("write", on_density_write)

        self.setup_icon()
        self.setup_ui()
        self.schedule_preview()

    def setup_icon(self):
        try:
            import AppKit
            app = AppKit.NSApplication.sharedApplication()
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "icon.png"))
            if os.path.exists(icon_path):
                icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                app.setApplicationIconImage_(icon)
        except ImportError:
            pass

    def setup_ui(self):
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(side="left", fill="y", padx=10, pady=10)

        def on_texture_change(choice):
            # Try to auto-select a matching palette
            match = next((p for p in self.palettes.keys() if choice in p), None)
            if match:
                self.palette_var.set(match)
            if choice == "Grass":
                self.subtype_cb.configure(state="normal")
            else:
                self.subtype_cb.configure(state="disabled")

        ctk.CTkLabel(ctrl_frame, text="Texture Type").pack(pady=(10, 0))
        ctk.CTkComboBox(ctrl_frame, variable=self.texture_var, values=self.textures, command=on_texture_change).pack()

        self.subtype_label = ctk.CTkLabel(ctrl_frame, text="Subtype")
        self.subtype_label.pack(pady=(10, 0))
        self.subtype_cb = ctk.CTkComboBox(ctrl_frame, variable=self.subtype_var, values=self.subtypes)
        self.subtype_cb.pack()
        
        # Initial state setup
        if self.texture_var.get() != "Grass":
            self.subtype_cb.configure(state="disabled")

        ctk.CTkLabel(ctrl_frame, text="Palette").pack(pady=(10, 0))
        palette_options = list(self.palettes.keys())
        self.palette_cb = ctk.CTkComboBox(ctrl_frame, variable=self.palette_var, values=palette_options)
        self.palette_cb.pack()

        # Custom Palette Frame (Always visible)
        self.custom_palette_frame = ctk.CTkFrame(ctrl_frame)
        self.custom_color_btns = []
        labels = ["Shadow", "Midtone 1", "Midtone 2", "Highlight"]
        for i in range(4):
            row_frame = ctk.CTkFrame(self.custom_palette_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row_frame, text=labels[i], width=80, anchor="w").pack(side="left", padx=5)
            
            def choose_color(idx=i):
                from tkinter.colorchooser import askcolor
                color = askcolor(color="#%02x%02x%02x" % self.custom_palette[idx], title=labels[idx])[0]
                if color:
                    self.custom_palette[idx] = (int(color[0]), int(color[1]), int(color[2]))
                    hex_color = "#%02x%02x%02x" % self.custom_palette[idx]
                    self.custom_color_btns[idx].configure(fg_color=hex_color, hover_color=hex_color)
                    self.schedule_preview()

            btn = ctk.CTkButton(row_frame, text="", width=30, height=20, command=choose_color)
            btn.pack(side="right", padx=5)
            self.custom_color_btns.append(btn)
            
        self.custom_palette_frame.pack(pady=10, fill="x")

        if self.texture_var.get() in self.palettes:
            self.palette_var.set(self.texture_var.get())
        else:
            self.palette_var.set(self.palette_var.get()) # Force init colors

        ctk.CTkLabel(ctrl_frame, text="Seed (0-9999)").pack(pady=(10, 0))
        self.seed_entry = ctk.CTkEntry(ctrl_frame, textvariable=self.seed_var)
        self.seed_entry.pack()

        self.seed_slider = ctk.CTkSlider(ctrl_frame, from_=0, to=9999, number_of_steps=9999)
        self.seed_slider.set(int(self.seed_var.get()))
        self.seed_slider.pack()

        def on_slider(val):
            self.seed_var.set(str(int(val)))
        self.seed_slider.configure(command=on_slider)

        ctk.CTkLabel(ctrl_frame, text="Density (1-100)").pack(pady=(10, 0))
        self.density_entry = ctk.CTkEntry(ctrl_frame, textvariable=self.density_var)
        self.density_entry.pack()

        self.density_slider = ctk.CTkSlider(ctrl_frame, from_=1, to=100, number_of_steps=99)
        self.density_slider.set(int(self.density_var.get()))
        self.density_slider.pack()

        def on_density_slider(val):
            self.density_var.set(str(int(val)))
        self.density_slider.configure(command=on_density_slider)

        self.btn_export = ctk.CTkButton(ctrl_frame, text="Export to Tiled", command=self.on_export, state="disabled")
        self.btn_export.pack(pady=20)

        self.lbl_status = ctk.CTkLabel(ctrl_frame, text="Ready.")
        self.lbl_status.pack()

        self.preview_frame = ctk.CTkFrame(self, width=300, height=450)
        self.preview_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.preview_frame, text="Single Tile (256x256)").pack(pady=(10, 0))
        self.lbl_preview = ctk.CTkLabel(self.preview_frame, text="No Preview")
        self.lbl_preview.pack(pady=5, expand=True)

        ctk.CTkLabel(self.preview_frame, text="3x3 Grid (96x96)").pack(pady=(10, 0))
        self.lbl_preview_3x3 = ctk.CTkLabel(self.preview_frame, text="No 3x3 Preview")
        self.lbl_preview_3x3.pack(pady=5, expand=True)

    def schedule_preview(self):
        if self._debounce_timer is not None:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(300, self.on_generate)

    def on_generate(self):
        self.btn_export.configure(state="disabled")
        self.lbl_status.configure(text="Generating preview...")

        try:
            seed_val = int(self.seed_var.get())
        except ValueError:
            seed_val = 0

        palette = list(self.custom_palette)

        try:
            density_val = int(self.density_var.get())
        except ValueError:
            density_val = 20

        params = {
            "texture_type": self.texture_var.get(),
            "seed": seed_val,
            "density": density_val,
            "palette": palette,
            "sub_type": self.subtype_var.get()
        }

        threading.Thread(target=self.generate_thread, kwargs=params, daemon=True).start()

    def generate_thread(self, texture_type, seed, density, palette, sub_type):
        try:
            noise = generate_texture(texture_type, seed, density, sub_type=sub_type)
            img_32 = quantize_image(noise, palette)

            img_256 = img_32.resize((256, 256), Image.Resampling.NEAREST)
            ctk_img = ctk.CTkImage(light_image=img_256, dark_image=img_256, size=(256, 256))

            img_96 = Image.new("RGB", (96, 96))
            for y in range(3):
                for x in range(3):
                    img_96.paste(img_32, (x * 32, y * 32))
            ctk_img_3x3 = ctk.CTkImage(light_image=img_96, dark_image=img_96, size=(96, 96))

            self.after(0, self.on_generate_success, img_32, ctk_img, ctk_img_3x3)
        except Exception as e:
            self.after(0, self.on_generate_error, f"Generation failed: {e}")

    def on_generate_success(self, img_32, ctk_img, ctk_img_3x3):
        self.current_img_32 = img_32
        self.lbl_preview.configure(image=ctk_img, text="")
        self.lbl_preview_3x3.configure(image=ctk_img_3x3, text="")
        self.lbl_status.configure(text="Ready to export.")
        self.btn_export.configure(state="normal")

    def on_generate_error(self, msg):
        self.lbl_status.configure(text=msg)
        self.btn_export.configure(state="disabled")

    def on_export(self):
        if not self.current_img_32:
            return
        
        texture_type = self.texture_var.get()
        try:
            seed_val = int(self.seed_var.get())
        except ValueError:
            seed_val = 0
            
        try:
            export_tile(self.current_img_32, texture_type, seed_val)
            self.lbl_status.configure(text=f"Exported to output/{texture_type}_{seed_val}.png")
        except PermissionError:
            self.lbl_status.configure(text="Cannot save files: permission denied in output/.")
        except Exception as e:
            self.lbl_status.configure(text=f"Export failed: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
