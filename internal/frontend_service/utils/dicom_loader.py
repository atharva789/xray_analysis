import os
import pydicom

def load_dicom_slices(folder_path):
    slices = []
    for file in sorted(os.listdir(folder_path)):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path):
            try:
                dcm = pydicom.dcmread(full_path, force=True)
                _ = dcm.pixel_array  # Validate it's a readable image
                slices.append(dcm)
            except:
                continue
    # Sort by InstanceNumber if available, fallback to order
    slices.sort(key=lambda x: int(getattr(x, "InstanceNumber", 0)))
    return slices