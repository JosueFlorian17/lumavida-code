"""
Módulo de Análisis de Reflectancia Cutánea ante Estímulos Cromáticos
Basado en Capítulo II (Reflectancia cutánea y dispersión subcutánea - Subsurface Scattering)
del documento LumaVida (UPCH).

Compara la señal lumínica proyectada en la pantalla con la respuesta fotométrica
observada en la piel del rostro para distinguir:
- Piel biológica real (difusión subdérmica y amortiguamiento espectral).
- Pantalla electrónica atacante (emisión propia no reactiva, reflejo de cristal polarizado).
- Fotografía en papel (reflexión especular plana de Fresnel sin absorción vascular).
"""

import numpy as np
from typing import List, Dict, Any, Tuple

class SkinReflectanceAnalyzer:
    def __init__(self, correlation_min: float = 0.22, specular_max_ratio: float = 0.35):
        self.correlation_min = correlation_min
        self.specular_max_ratio = specular_max_ratio

    def analyze_reflectance(
        self,
        projected_colors: List[Dict[str, float]], # [{"r": 255, "g": 0, "b": 128, "timestamp": ...}]
        observed_skin_colors: List[Dict[str, float]], # [{"r": ..., "g": ..., "b": ..., "timestamp": ...}]
        roi_images: List[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Evalúa la correspondencia fotométrica y de dispersión entre estímulo y piel,
        compensando el desfase temporal natural (latencia de hardware cámara-pantalla de 0 a 100 ms).
        """
        n_proj = len(projected_colors)
        n_obs = len(observed_skin_colors)

        if n_obs < 15 or n_proj < 15:
            return {
                "is_live": False,
                "reflectance_score": 0.0,
                "correlation": 0.0,
                "diffusion_score": 0.0,
                "specular_ratio": 1.0,
                "reason": "Muestras insuficientes de frames durante el estímulo lumínico"
            }

        min_len = min(n_proj, n_obs)
        proj_r = np.array([projected_colors[i]["r"] for i in range(min_len)], dtype=np.float64)
        proj_g = np.array([projected_colors[i]["g"] for i in range(min_len)], dtype=np.float64)
        proj_b = np.array([projected_colors[i]["b"] for i in range(min_len)], dtype=np.float64)

        obs_r = np.array([observed_skin_colors[i]["r"] for i in range(min_len)], dtype=np.float64)
        obs_g = np.array([observed_skin_colors[i]["g"] for i in range(min_len)], dtype=np.float64)
        obs_b = np.array([observed_skin_colors[i]["b"] for i in range(min_len)], dtype=np.float64)

        # 1. Luminancia relativa proyectada vs. observada (Y = 0.299R + 0.587G + 0.114B)
        proj_lum = 0.299 * proj_r + 0.587 * proj_g + 0.114 * proj_b
        obs_lum = 0.299 * obs_r + 0.587 * obs_g + 0.114 * obs_b

        std_p = np.std(proj_lum)
        std_o = np.std(obs_lum)

        # Correlación con compensación de desfase temporal (Lagged Cross-Correlation de 0 a 3 frames)
        corr_lum = self._lagged_pearson(proj_lum, obs_lum, max_lag=3)
        corr_r = self._lagged_pearson(proj_r, obs_r, max_lag=3)
        corr_g = self._lagged_pearson(proj_g, obs_g, max_lag=3)
        corr_b = self._lagged_pearson(proj_b, obs_b, max_lag=3)
        
        # Correlación cromática ponderada (el canal verde y rojo absorben la hemoglobina y dispersión de la piel)
        avg_chroma_corr = float(0.35 * corr_r + 0.45 * corr_g + 0.20 * corr_b)

        # 2. Análisis de Dispersión Subcutánea vs. Reflejo Especular
        specular_ratio = 0.0

        if roi_images and len(roi_images) > 0:
            specular_counts = []
            for roi in roi_images:
                if roi is not None and roi.size > 0:
                    # En espacio de color HSV, brillos especulares intensos de cristal OLED/LCD presentan Value > 248 y Saturation < 25
                    try:
                        import cv2
                        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        specular_mask = (hsv[:, :, 2] > 248) & (hsv[:, :, 1] < 25)
                        ratio = np.count_nonzero(specular_mask) / (roi.shape[0] * roi.shape[1])
                        specular_counts.append(ratio)
                    except Exception:
                        pass
            if specular_counts:
                specular_ratio = float(np.mean(specular_counts))
        else:
            specular_ratio = float(max(0.0, min(1.0, std_o / (np.mean(obs_lum) + 1e-5) - 0.5)))

        # 3. Puntuación de Reflectancia Cutánea
        base_score = max(0.0, avg_chroma_corr)
        penalty_specular = max(0.0, specular_ratio - self.specular_max_ratio) * 1.5
        reflectance_score = float(np.clip(base_score - penalty_specular, 0.0, 1.0))

        # La piel viva reacciona coherentemente con el flash (corr >= 0.22 en presencia de luz ambiental)
        # y no presenta saturación reflectiva de cristal de celular (specular_ratio <= 0.35)
        # ni es una cámara congelada/foto plana (std_o > 0.08)
        is_live = (
            avg_chroma_corr >= self.correlation_min and
            specular_ratio <= 0.35 and
            std_o > 0.08
        )

        reason = "Reflectancia biológica cutánea consistente" if is_live else (
            "Reflejo especular anómalo de pantalla secundaria" if specular_ratio > 0.35 else
            "Ausencia de modulación cutánea ante el estímulo cromático (foto estática o iluminación insuficiente)"
        )

        return {
            "is_live": bool(is_live),
            "reflectance_score": round(reflectance_score, 4),
            "correlation": round(avg_chroma_corr, 4),
            "luminance_correlation": round(corr_lum, 4),
            "specular_ratio": round(specular_ratio, 4),
            "std_observed": round(float(std_o), 4),
            "reason": reason
        }

    def _lagged_pearson(self, x: np.ndarray, y: np.ndarray, max_lag: int = 3) -> float:
        """
        Calcula la máxima correlación de Pearson evaluando retardos temporales de 0 a max_lag cuadros.
        Compensa la latencia de captura y renderizado de la cámara web.
        """
        best_corr = -1.0
        n = len(x)
        if n < 5:
            return 0.0

        for lag in range(0, min(max_lag + 1, n // 3)):
            if lag == 0:
                xi = x
                yi = y
            else:
                xi = x[:-lag]
                yi = y[lag:]
            
            c = self._pearson(xi, yi)
            if c > best_corr:
                best_corr = c
                
        return max(0.0, best_corr)

    def _pearson(self, x: np.ndarray, y: np.ndarray) -> float:
        x_norm = x - np.mean(x)
        y_norm = y - np.mean(y)
        std_x = np.std(x_norm)
        std_y = np.std(y_norm)
        if std_x < 1e-5 or std_y < 1e-5:
            return 0.0
        return float(np.dot(x_norm, y_norm) / (len(x_norm) * std_x * std_y))
