"""
Módulo de Fotopletismografía Remota (rPPG)
Basado en Capítulo II (Señal fisiológica de pulso cardíaco en canales G/R - DeepFakesON-Phys)
del documento LumaVida (UPCH).

Extrae la onda pletismográfica del flujo de microvascularización facial mediante el
algoritmo CHROM (de Haan & Jeanne) y POS (Plane-Orthogonal-to-Skin), filtrado pasabanda
Butterworth y análisis espectral FFT para verificación de pulso cardíaco real.
"""

import numpy as np
from scipy import signal
from typing import List, Dict, Any, Tuple

class RPPGAnalyzer:
    def __init__(
        self,
        fps: float = 30.0,
        min_freq: float = 0.7,   # ~42 BPM
        max_freq: float = 3.5,   # ~210 BPM
        snr_threshold: float = 0.38,
        peak_prominence_min: float = 1.8
    ):
        self.fps = fps
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.snr_threshold = snr_threshold
        self.peak_prominence_min = peak_prominence_min

    def extract_pulse_chrom(self, rgb_signals: List[Tuple[float, float, float]]) -> np.ndarray:
        """
        Aplica el algoritmo CHROM (Chrominance method):
        Proyecta los canales R, G, B en dos señales de crominancia ortogonales
        para eliminar artefactos de iluminación ambiental y aislar la variación
        de volumen sanguíneo pulsátil.
        """
        if len(rgb_signals) < 10:
            return np.array([])

        signals_arr = np.array(rgb_signals, dtype=np.float64) # Shape: (N, 3)
        R = signals_arr[:, 0]
        G = signals_arr[:, 1]
        B = signals_arr[:, 2]

        # Normalización temporal por la media móvil
        mean_R = np.mean(R) + 1e-6
        mean_G = np.mean(G) + 1e-6
        mean_B = np.mean(B) + 1e-6

        Rn = R / mean_R
        Gn = G / mean_G
        Bn = B / mean_B

        # Señales de crominancia ortogonales
        # Xs = 3Rn - 2Gn
        # Ys = 1.5Rn + Gn - 1.5Bn
        Xs = 3.0 * Rn - 2.0 * Gn
        Ys = 1.5 * Rn + Gn - 1.5 * Bn

        std_Xs = np.std(Xs)
        std_Ys = np.std(Ys) + 1e-6
        alpha = std_Xs / std_Ys

        # Señal rPPG bruta
        bvp = Xs - alpha * Ys
        return bvp

    def bandpass_filter(self, raw_signal: np.ndarray, sampling_rate: float) -> np.ndarray:
        """
        Filtro pasabanda Butterworth orden 3 en ventana fisiológica [0.7, 3.5] Hz.
        """
        if len(raw_signal) < 15:
            return raw_signal
        
        nyquist = 0.5 * sampling_rate
        low = self.min_freq / nyquist
        high = min(0.95, self.max_freq / nyquist)

        if low >= high or low <= 0:
            return raw_signal - np.mean(raw_signal)

        try:
            b, a = signal.butter(3, [low, high], btype='bandpass')
            # Usar filtfilt para evitar desfase de fase
            filtered = signal.filtfilt(b, a, raw_signal)
            return filtered
        except Exception:
            return raw_signal - np.mean(raw_signal)

    def analyze_rppg(self, rgb_series: List[Tuple[float, float, float]], sampling_rate: float = 30.0) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de rPPG:
        1. Extracción de señal BVP con CHROM.
        2. Filtrado pasabanda.
        3. Densidad espectral FFT y pico cardíaco.
        4. Estimación de SNR y dictamen de pulso humano vivo.
        """
        n_samples = len(rgb_series)
        effective_fps = max(10.0, float(sampling_rate))

        if n_samples < 25:
            return {
                "is_live": False,
                "bpm": 0.0,
                "snr": 0.0,
                "confidence": 0.0,
                "bvp_waveform": [],
                "frequencies": [],
                "psd": [],
                "reason": "Muestras insuficientes para estimación de pulso cardíaco rPPG"
            }

        # 1. Extracción BVP (Blood Volume Pulse)
        raw_bvp = self.extract_pulse_chrom(rgb_series)
        filtered_bvp = self.bandpass_filter(raw_bvp, effective_fps)

        # 2. Análisis Espectral (FFT)
        # Zero-padding para mejorar resolución en frecuencia
        n_fft = max(256, int(2 ** np.ceil(np.log2(n_samples * 4))))
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / effective_fps)
        fft_magnitude = np.abs(np.fft.rfft(filtered_bvp - np.mean(filtered_bvp), n=n_fft)) ** 2

        # Rango fisiológico [0.7 Hz, 3.5 Hz]
        physio_indices = np.where((freqs >= self.min_freq) & (freqs <= self.max_freq))[0]
        
        if len(physio_indices) == 0:
            return {
                "is_live": False,
                "bpm": 0.0,
                "snr": 0.0,
                "confidence": 0.0,
                "bvp_waveform": filtered_bvp.tolist(),
                "frequencies": [],
                "psd": [],
                "reason": "Espectro rPPG fuera del rango fisiológico humano"
            }

        physio_freqs = freqs[physio_indices]
        physio_psd = fft_magnitude[physio_indices]

        # Encontrar pico principal
        peak_idx_local = np.argmax(physio_psd)
        dominant_freq = physio_freqs[peak_idx_local]
        peak_power = physio_psd[peak_idx_local]
        estimated_bpm = float(dominant_freq * 60.0)

        # 3. Cálculo de SNR del pulso y prominencia para ventanas cortas (< 2.5 s)
        # En ventanas cortas de ~60 cuadros, el lóbulo principal de la FFT ocupa +- 0.20 Hz
        peak_mask = np.abs(physio_freqs - dominant_freq) <= 0.20
        
        # Considerar también el primer armónico si cae dentro del rango fisiológico
        harmonic_freq = 2.0 * dominant_freq
        if harmonic_freq <= self.max_freq:
            harmonic_mask = np.abs(physio_freqs - harmonic_freq) <= 0.20
            signal_mask = peak_mask | harmonic_mask
        else:
            signal_mask = peak_mask

        signal_power = np.sum(physio_psd[signal_mask])
        noise_power = np.sum(physio_psd[~signal_mask]) + 1e-6
        snr = float(signal_power / noise_power)

        # Prominencia del pico respecto al piso de ruido mediano
        median_noise = float(np.median(physio_psd)) + 1e-6
        prominence_ratio = float(peak_power / median_noise)

        # Amplitud pico a pico de la onda pletismográfica (la sangre genera ptp >= 0.0012)
        bvp_ptp = float(np.ptp(filtered_bvp))
        has_hemodynamic_amplitude = bvp_ptp >= 0.0012

        # Evaluación de consistencia biológica:
        # 1. Rango de frecuencia cardíaca fisiológica humana (48 - 180 BPM)
        # 2. SNR pulsátil >= umbral (0.38 calibrado para ventanas de ~2s)
        # 3. Potencia y amplitud mínima de la onda volumétrica sanguínea
        is_physio_range = 48.0 <= estimated_bpm <= 180.0
        has_pulse_signature = (snr >= self.snr_threshold) and (prominence_ratio >= self.peak_prominence_min)
        has_min_power = peak_power > 5e-6

        is_live = bool(is_physio_range and has_pulse_signature and has_min_power and has_hemodynamic_amplitude)

        # Calibración de confianza porcentual realista
        # Mapea un SNR de 0.35 - 0.85 a una confianza de 60% - 95%
        norm_snr = np.clip((snr - 0.25) / 0.60, 0.0, 1.0)
        confidence = float(np.clip(0.40 + 0.55 * norm_snr, 0.10, 0.98)) if is_live else float(np.clip(snr / 1.5, 0.05, 0.35))

        # Downsample de forma de onda y espectro para serializar limpio en JSON
        step = max(1, len(filtered_bvp) // 60)
        downsampled_waveform = [round(float(v), 4) for v in filtered_bvp[::step]]
        
        step_psd = max(1, len(physio_freqs) // 35)
        serialized_freqs = [round(float(f * 60.0), 1) for f in physio_freqs[::step_psd]]
        serialized_psd = [round(float(p), 4) for p in physio_psd[::step_psd]]

        reason = (
            f"Pulso cardíaco humano detectado ({estimated_bpm:.1f} BPM, SNR: {snr:.2f}, Prominencia: {prominence_ratio:.1f}x)"
            if is_live else
            f"Señal pulsátil insuficiente o ruido plano (BPM est: {estimated_bpm:.1f}, SNR: {snr:.2f} < {self.snr_threshold})"
        )

        return {
            "is_live": is_live,
            "bpm": round(estimated_bpm, 1),
            "snr": round(snr, 3),
            "prominence_ratio": round(prominence_ratio, 2),
            "confidence": round(confidence, 3),
            "bvp_waveform": downsampled_waveform,
            "frequencies": serialized_freqs,
            "psd": serialized_psd,
            "reason": reason
        }
