"""
Módulo de Detección Facial y Extracción de Regiones de Interés (ROIs) Cutáneas
Alineado al Capítulo II y III de la investigación LumaVida (UPCH).

Extrae tres zonas clave de la piel humana:
1. Frente (alta vascularización, baja interferencia pilosa).
2. Pómulo/mejilla izquierda.
3. Pómulo/mejilla derecha.
Aplica máscara cromática adaptativa (espacio YCrCb) para aislar tejido biológico.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, List

class FaceROIExtractor:
    def __init__(self):
        # Cargar clasificador facial frontal en cascada estándar optimizado de OpenCV
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_face_bbox(self, frame_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detecta el rostro dominante en el cuadro. Retorna (x, y, w, h) o None.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )
        if len(faces) == 0:
            return None
        # Seleccionar el rostro con mayor área (el más cercano/principal)
        main_face = max(faces, key=lambda b: b[2] * b[3])
        return tuple(int(v) for v in main_face)

    def extract_skin_rois(self, frame_bgr: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, np.ndarray]:
        """
        Dada la caja delimitadora del rostro, extrae subregiones biológicas:
        - forehead: ~20% superior, central
        - left_cheek: región media izquierda
        - right_cheek: región media derecha
        """
        x, y, w, h = bbox
        
        # 1. Frente (Forehead)
        # y: 15% a 32% del alto, x: 28% a 72% del ancho
        fh_y1 = int(y + 0.15 * h)
        fh_y2 = int(y + 0.32 * h)
        fh_x1 = int(x + 0.28 * w)
        fh_x2 = int(x + 0.72 * w)
        forehead = frame_bgr[max(0, fh_y1):min(frame_bgr.shape[0], fh_y2),
                             max(0, fh_x1):min(frame_bgr.shape[1], fh_x2)]
        
        # 2. Pómulo Izquierdo (Left Cheek)
        # y: 48% a 68% del alto, x: 18% a 40% del ancho
        lc_y1 = int(y + 0.48 * h)
        lc_y2 = int(y + 0.68 * h)
        lc_x1 = int(x + 0.18 * w)
        lc_x2 = int(x + 0.40 * w)
        left_cheek = frame_bgr[max(0, lc_y1):min(frame_bgr.shape[0], lc_y2),
                               max(0, lc_x1):min(frame_bgr.shape[1], lc_x2)]
        
        # 3. Pómulo Derecho (Right Cheek)
        # y: 48% a 68% del alto, x: 60% a 82% del ancho
        rc_y1 = int(y + 0.48 * h)
        rc_y2 = int(y + 0.68 * h)
        rc_x1 = int(x + 0.60 * w)
        rc_x2 = int(x + 0.82 * w)
        right_cheek = frame_bgr[max(0, rc_y1):min(frame_bgr.shape[0], rc_y2),
                                max(0, rc_x1):min(frame_bgr.shape[1], rc_x2)]

        return {
            "forehead": forehead,
            "left_cheek": left_cheek,
            "right_cheek": right_cheek
        }

    def get_skin_mask(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Segmentación cromática en espacio YCrCb para aislar píxeles de piel humana,
        evitando brillos especulares extremos o fondos oscuros.
        """
        if img_bgr.size == 0:
            return np.zeros((0, 0), dtype=np.uint8)
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        # Rango empírico representativo de piel humana en YCrCb
        lower_skin = np.array([40, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 175, 130], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        return mask

    def compute_roi_mean_rgb(self, roi_bgr: np.ndarray) -> Tuple[float, float, float]:
        """
        Calcula el valor promedio (R, G, B) de la piel en una ROI,
        filtrando píxeles no representativos mediante la máscara cutánea.
        """
        if roi_bgr.size == 0:
            return (0.0, 0.0, 0.0)
        
        mask = self.get_skin_mask(roi_bgr)
        # Si la máscara es muy pequeña, usar toda la región recortada
        if np.count_nonzero(mask) < (roi_bgr.shape[0] * roi_bgr.shape[1] * 0.1):
            b_mean = float(np.mean(roi_bgr[:, :, 0]))
            g_mean = float(np.mean(roi_bgr[:, :, 1]))
            r_mean = float(np.mean(roi_bgr[:, :, 2]))
        else:
            b_mean = float(np.mean(roi_bgr[:, :, 0][mask > 0]))
            g_mean = float(np.mean(roi_bgr[:, :, 1][mask > 0]))
            r_mean = float(np.mean(roi_bgr[:, :, 2][mask > 0]))
            
        return (r_mean, g_mean, b_mean)
