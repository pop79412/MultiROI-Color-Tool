import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageGrab, ImageTk, ImageDraw, Image
import numpy as np
import math, csv, os
from datetime import datetime
import ctypes
from PIL import ImageFont

# solve different DPI problem
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# =========================================================
# ROI Analysis 
# =========================================================
def analyze_roi_imatest_style(
    img,
    signal_definition="mean",
    trim_percent=0
):

    img_np = np.asarray(img).astype(np.float64)
    h, w, _ = img_np.shape

    # process luminance by Rec.601

    L_map = 0.2125*img_np[:,:,0] + 0.7154*img_np[:,:,1] + 0.0721*img_np[:,:,2]

    # Second-order polynomial fitting for detrending luminance variations caused by lens shading or non-uniform illumination
    y, x = np.mgrid[:h, :w]
    x_f, y_f, L_f = x.ravel(), y.ravel(), L_map.ravel()

    A = np.column_stack([x_f**2, y_f**2, x_f*y_f, x_f, y_f, np.ones_like(x_f)])
    coeffs, _, _, _ = np.linalg.lstsq(A, L_f, rcond=None)
    trend = (A @ coeffs).reshape(h, w)

    # Calculate noise by subtracting the trend surface from the original luminance map
    # (Detrending: Removing variations caused by lens shading or non-uniform illumination)
    noise = (L_map - trend).ravel()
    # Optional: Outlier removal using percentile trimming
    if trim_percent and 0 < trim_percent < 50:
        lo, hi = np.percentile(noise, [trim_percent, 100-trim_percent])
        noise = noise[(noise>=lo) & (noise<=hi)]
    # Calculate standard deviation of the noise floor
    std_noise = np.std(noise, ddof=0)

    # Define the signal intensity based on the selected method
    if signal_definition == "trend":
        signal = float(np.mean(trend))
    else:
        signal = float(np.mean(L_map))

    # Calculate Signal-to-Noise Ratio (SNR) in decibels (dB)
    snr_db = 20*math.log10(signal/std_noise) if std_noise>0 else float("inf")

    # Calculate mean RGB values for reporting
    r_mean, g_mean, b_mean = np.mean(img_np, axis=(0, 1))

    return int(round(r_mean)), int(round(g_mean)), int(round(b_mean)), signal, snr_db


# =========================================================
# Main Tool GUI Class
# =========================================================
class MultiROITool:
    def __init__(self, root):
        self.root = root
        self.root.title("MultiROI-Color-Tool")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        self.image = None
        self.source_mode = None  # "screenshot" | "load"
        self.rois = []

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack()

        btns = ttk.Frame(frm)
        btns.pack(anchor="w")

        ttk.Button(btns, text="Snap and Crop", command=self.start_capture).pack(side=tk.LEFT)
        ttk.Button(btns, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Save Results", command=self.save_txtresults).pack(side=tk.LEFT, padx=6)

        self.var_info = tk.StringVar(value="")
        ttk.Label(frm, textvariable=self.var_info, font=("Consolas", 10), justify="left")\
            .pack(anchor="w", pady=(8, 0))

        self.preview = tk.Canvas(frm, width=160, height=160, highlightthickness=1)
        self.preview.pack(pady=6)
        self.preview_img = None

        ttk.Label(frm, text="Esc：Crop Finish", foreground="#666").pack(anchor="w")

    def start_capture(self):
        self.image = ImageGrab.grab(all_screens=False)
        self.source_mode = "screenshot"
        self.rois.clear()
        ROISelector(self.root, self.image, self.on_new_roi, mode="screenshot")

    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")]
        )
        if not path:
            return
        self.image = Image.open(path).convert("RGB")
        self.source_mode = "load"
        self.rois.clear()
        ROISelector(self.root, self.image, self.on_new_roi, mode="load")

    def on_new_roi(self, roi):
        self.rois.append(roi)
        r, g, b = roi["rgb"]
        self.var_info.set(
            f"ROI #{roi['id']}\n"
            f"RGB(avg): {r}, {g}, {b}\n"
            f"L(avg): {roi['L']:.2f}\n"
            f"L SNR: {roi['snr']:.2f} dB\n"
        )

        patch = roi["img"].resize((160, 160))
        self.preview_img = ImageTk.PhotoImage(patch)
        self.preview.delete("all")
        self.preview.create_image(0, 0, image=self.preview_img, anchor="nw")

    def save_txtresults(self):
        if not self.image or not self.rois:
            messagebox.showwarning("No ROI data!", "Still not crop ROI")
            return

        default_path = os.path.join(os.path.expanduser("~"), "Desktop")
        out_dir = filedialog.askdirectory(title="choose folder", initialdir=default_path)
        if not out_dir:
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ---- 1. Save copy image ----
        img = self.image.copy()
        draw = ImageDraw.Draw(img)
        font_size = 48
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()  # avoid Font not found

        for roi in self.rois:
            x0, y0, x1, y1 = roi["bbox"]
            draw.rectangle((x0, y0, x1, y1), outline="red", width=5)
            draw.text((x0+5, y0+5), str(roi["id"]), fill="red", font=font)

        img.save(os.path.join(out_dir, f"Analysis_Result_{ts}.png"))

        # ---- 2. Save results Log ----
        txt_path = os.path.join(out_dir, f"Analysis_Log_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Color Probe ROI Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 85 + "\n")
            header = f"{'ID':<4} {'x0':<6} {'y0':<6} {'x1':<6} {'y1':<6} {'R':<4} {'G':<4} {'B':<4} {'L':<10} {'L_SNR(dB)':<8}\n"
            f.write(header)
            f.write("-" * 85 + "\n")
            for roi in self.rois:
                x0,y0,x1,y1 = roi["bbox"]
                r,g,b = roi["rgb"]
                line = (f"{roi['id']:<4} {x0:<6} {y0:<6} {x1:<6} {y1:<6} "
                        f"{r:<4} {g:<4} {b:<4} {roi['L']:<10.3f} {roi['snr']:<8.2f}\n")
                f.write(line)
            f.write("-" * 85 + "\n")
            f.write(f"Total ROIs: {len(self.rois)}\n")
        messagebox.showinfo("Finish!", f"Result data save to\nPath: {out_dir}")


    def save_results_csv(self):
        if not self.image or not self.rois:
            messagebox.showwarning("No ROI data!", "Still not crop ROI")
            return

        out_dir = filedialog.askdirectory()
        if not out_dir:
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        img = self.image.copy()
        draw = ImageDraw.Draw(img)

        for roi in self.rois:
            x0, y0, x1, y1 = roi["bbox"]
            draw.rectangle((x0, y0, x1, y1), outline="red", width=2)
            draw.text((x0 + 5, y0 + 5), str(roi["id"]), fill="red")

        img.save(os.path.join(out_dir, f"ColorPick_{ts}.png"))

        with open(os.path.join(out_dir, f"ColorPick_roi_log_{ts}.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "x0", "y0", "x1", "y1", "R", "G", "B", "L", "L_SNR_dB"])
            for roi in self.rois:
                writer.writerow([
                    roi["id"],
                    *roi["bbox"],
                    *roi["rgb"],
                    f"{roi['L']:.3f}",
                    f"{roi['snr']:.2f}"
                ])
        messagebox.showinfo("Finish", f"CSV Data output at: {out_dir}")

# =========================================================
# GUI Interaction: ROI Selection Canvas
# =========================================================
class ROISelector(tk.Toplevel):
    def __init__(self, parent, image, callback, mode):
        super().__init__(parent)
        self.image = image
        self.callback = callback
        self.mode = mode
        self.roi_count = 0

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.canvas = tk.Canvas(self, bg="black", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.after(50, self._render)

        self.start_x = self.start_y = 0
        self.temp_rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.bind("<Escape>", lambda e: self.destroy())

    def _render(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.image.size

        if self.mode == "screenshot":
            disp = self.image
        else:
            # Count scale ratio
            self.scale = min(cw/iw, ch/ih)
            disp = self.image.resize((int(iw*self.scale), int(ih*self.scale)))
            self.offset_x = (cw - disp.size[0])//2
            self.offset_y = (ch - disp.size[1])//2

        self.tkimg = ImageTk.PhotoImage(disp)
        self.canvas.create_image(self.offset_x, self.offset_y, image=self.tkimg, anchor="nw")

    def on_down(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.temp_rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def on_drag(self, e):
        self.canvas.coords(self.temp_rect, self.start_x, self.start_y, e.x, e.y)

    def on_up(self, e):
        dx0, dy0 = min(self.start_x,e.x), min(self.start_y,e.y)
        dx1, dy1 = max(self.start_x,e.x), max(self.start_y,e.y)

        # Get original position
        if self.mode == "load":
            x0 = int((dx0 - self.offset_x)/self.scale)
            x1 = int((dx1 - self.offset_x)/self.scale)
            y0 = int((dy0 - self.offset_y)/self.scale)
            y1 = int((dy1 - self.offset_y)/self.scale)
        else:
            x0,y0,x1,y1 = dx0,dy0,dx1,dy1

        if x1<=x0 or y1<=y0:
            return

        self.roi_count += 1
        roi_img = self.image.crop((x0,y0,x1,y1))
        r,g,b,L,snr = analyze_roi_imatest_style(roi_img)

        # Tag ID
        self.canvas.create_text(dx0+6, dy0+6, text=str(self.roi_count),
                                fill="red", font=("Arial",18,"bold"), anchor="nw")

        self.callback({
            "id": self.roi_count,
            "bbox": (x0,y0,x1,y1),
            "rgb": (r,g,b),
            "L": L,
            "snr": snr,
            "img": roi_img
        })

        self.master.lift()
        self.temp_rect = None


if __name__ == "__main__":
    root = tk.Tk()
    MultiROITool(root)
    root.mainloop()
