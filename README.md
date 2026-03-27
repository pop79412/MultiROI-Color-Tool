# MultiROI-Color-Tool
Extract RGB, Luminance, and SNR data from multiple regions of interest (ROI). Features include real-time screen cropping, image inspection, and Text report generation.


## ✨ Key Features
- **Multi-ROI Selection**: Select multiple areas on a screenshot or a loaded image.
- **Imatest-style SNR**: Calculates Signal-to-Noise Ratio using trend-removal algorithms.
- **Data Export**: Automatically generates a marked result image and a detailed data log
- **High Precision**: Built-in support for Windows DPI awareness for accurate screen capturing.

## 🛠 Tech Stack
- **Language**: Python 3.x
- **Libraries**: Tkinter (UI), Pillow (Image Processing), NumPy (Calculations)

## 🚀 Quick Start
1. Clone the repo: `git clone https://github.com/pop79412/MultiROI-Color-Tool.git`
2. Install dependencies: `pip install pillow numpy`
3. Run the tool: `python MultiROI-Color-Tool.py`
4. Capture screen button or load image button
5. Crop multi ROI and Save log & Image if needed

## 📊 Output Data
- **RGB**: Average Red, Green, and Blue values per ROI.
- **Luminance (L)**: Calculated brightness value.
- **SNR (dB)**: Signal-to-noise ratio in decibels for noise floor analysis.
