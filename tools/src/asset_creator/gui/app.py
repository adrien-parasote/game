import contextlib
import os
import random
import threading

import customtkinter as ctk
from asset_creator.core.generator import generate
from asset_creator.core.quantizer import load_palettes, quantize
from asset_creator.exporters.exporter import derive_tile_name, export
from PIL import Image

DEFAULT_TEXTURES = ["Stone", "Grass", "Water", "Dirt", "Wood"]
DEFAULT_PALETTE = {
    "PICO-8 (Full)": [(0,0,0), (29,43,83), (126,37,83), (0,135,81), (171,82,54), (95,87,79),
               (194,195,199), (255,241,232), (255,0,77), (255,163,0), (255,236,39),
               (0,228,54), (41,173,255), (131,118,156), (255,119,168), (255,204,170)],
    "Grass": [(26,58,15), (45,90,27), (67,123,40), (90,158,54)],
    "Stone": [(0,0,0), (95,87,79), (194,195,199), (255,241,232)],
    "Water": [(29,43,83), (41,173,255), (131,118,156), (194,195,199)],
    "Dirt": [(0,0,0), (126,37,83), (171,82,54), (255,163,0)],
    "Wood": [(0,0,0), (126,37,83), (171,82,54), (255,204,170)]
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Asset Creator - Procedural")
        self.geometry("600x600")

        self.textures = DEFAULT_TEXTURES
        self.palettes = DEFAULT_PALETTE

        if os.path.exists("textures.json"):
            import json
            try:
                with open("textures.json", encoding="utf-8") as f:
                    self.textures = json.load(f)
            except Exception:
                pass

        if os.path.exists("palettes.json"):
            with contextlib.suppress(Exception):
                self.palettes = load_palettes("palettes.json")

        if not self.palettes:
            self.palettes = DEFAULT_PALETTE

        self.texture_var = ctk.StringVar(value=self.textures[0])
        self.palette_var = ctk.StringVar(value=next(iter(self.palettes.keys())))

        initial_seed = random.randint(0, 9999)
        self.seed_var = ctk.StringVar(value=str(initial_seed))
        self.scale_var = ctk.DoubleVar(value=4.0)

        self.setup_icon()
        self.setup_ui()

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
            if choice in self.palettes:
                self.palette_var.set(choice)

        ctk.CTkLabel(ctrl_frame, text="Texture Type").pack(pady=(10, 0))
        ctk.CTkComboBox(ctrl_frame, variable=self.texture_var, values=self.textures, command=on_texture_change).pack()

        ctk.CTkLabel(ctrl_frame, text="Palette").pack(pady=(10, 0))
        ctk.CTkComboBox(ctrl_frame, variable=self.palette_var, values=list(self.palettes.keys())).pack()

        if self.texture_var.get() in self.palettes:
            self.palette_var.set(self.texture_var.get())

        ctk.CTkLabel(ctrl_frame, text="Seed (0-9999)").pack(pady=(10, 0))
        self.seed_entry = ctk.CTkEntry(ctrl_frame, textvariable=self.seed_var)
        self.seed_entry.pack()

        self.seed_slider = ctk.CTkSlider(ctrl_frame, from_=0, to=9999, number_of_steps=9999)
        self.seed_slider.set(int(self.seed_var.get()))
        self.seed_slider.pack()

        def on_slider(val):
            self.seed_var.set(str(int(val)))
        self.seed_slider.configure(command=on_slider)

        ctk.CTkLabel(ctrl_frame, text="Scale (1-10)").pack(pady=(10, 0))
        ctk.CTkSlider(ctrl_frame, variable=self.scale_var, from_=1, to=10, number_of_steps=9).pack()

        self.btn_generate = ctk.CTkButton(ctrl_frame, text="Generate", command=self.on_generate)
        self.btn_generate.pack(pady=20)

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

    def on_generate(self):
        self.btn_generate.configure(state="disabled")
        self.lbl_status.configure(text="Generating...")

        try:
            seed_val = int(self.seed_var.get())
        except ValueError:
            seed_val = 0

        palette = self.palettes.get(self.palette_var.get())
        if not palette:
            palette = next(iter(self.palettes.values()))

        params = {
            "texture_type": self.texture_var.get(),
            "seed": seed_val,
            "scale": self.scale_var.get(),
            "palette": palette
        }

        threading.Thread(target=self.generate_thread, kwargs=params, daemon=True).start()

    def generate_thread(self, texture_type, seed, scale, palette):
        try:
            noise = generate(texture_type, seed, scale)
            img_32 = quantize(noise, palette)
            tile_name = derive_tile_name(texture_type, seed)
            export(img_32, tile_name)

            img_256 = img_32.resize((256, 256), Image.Resampling.NEAREST)
            ctk_img = ctk.CTkImage(light_image=img_256, dark_image=img_256, size=(256, 256))

            img_96 = Image.new("RGB", (96, 96))
            for y in range(3):
                for x in range(3):
                    img_96.paste(img_32, (x * 32, y * 32))
            ctk_img_3x3 = ctk.CTkImage(light_image=img_96, dark_image=img_96, size=(96, 96))

            self.after(0, self.on_generate_success, ctk_img, ctk_img_3x3)
        except PermissionError:
            self.after(0, self.on_generate_error, "Cannot save files: permission denied in output/.")
        except Exception as e:
            self.after(0, self.on_generate_error, f"Generation failed: {e}")

    def on_generate_success(self, ctk_img, ctk_img_3x3):
        self.lbl_preview.configure(image=ctk_img, text="")
        self.lbl_preview_3x3.configure(image=ctk_img_3x3, text="")
        self.lbl_status.configure(text="Done.")
        self.btn_generate.configure(state="normal")

    def on_generate_error(self, msg):
        self.lbl_status.configure(text=msg)
        self.btn_generate.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()
