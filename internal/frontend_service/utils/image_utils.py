import numpy as np
from PyQt5.QtGui import QImage
import pydicom

def apply_windowing(pixel_array, center, width):
    img = pixel_array.astype(np.float32)
    lower = center - (width / 2)
    upper = center + (width / 2)
    img = np.clip(img, lower, upper)
    return ((img - lower) / (upper - lower)) * 255

def get_qimage(dcm):
    img = dcm.pixel_array.astype(np.float32)
    slope = float(getattr(dcm, "RescaleSlope", 1))
    intercept = float(getattr(dcm, "RescaleIntercept", 0))
    img = img * slope + intercept

    center = float(dcm.WindowCenter[0]) if isinstance(dcm.WindowCenter, pydicom.multival.MultiValue) else float(dcm.WindowCenter)
    width = float(dcm.WindowWidth[0]) if isinstance(dcm.WindowWidth, pydicom.multival.MultiValue) else float(dcm.WindowWidth)

    img = apply_windowing(img, center, width).astype(np.uint8)

    if dcm.PhotometricInterpretation == "MONOCHROME1":
        img = 255 - img

    rgb = np.stack([img] * 3, axis=-1)
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)