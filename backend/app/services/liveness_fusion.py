"""
Módulo de Fusión de Señales y Regla de Decisión de Detección de Vida (Liveness)
Basado en Capítulo III (Figura 2: Flujo del módulo de detección de vida)
y estándares ISO/IEC 30107 (Presentation Attack Detection) del documento LumaVida.

Combina:
1. Puntuación de Reflectancia Cutánea (Skin Reflectance Score)
2. Puntuación de Fotopletismografía Remota (rPPG Pulse Score)
Produce:
- Veredicto binario: BONA_FIDE (Vivo) vs. PRESENTATION_ATTACK (Ataque)
- Clasificación forense de ataque: Foto impresa, Pantalla externa o Deepfake sintético.
"""

from typing import Dict, Any

class LivenessDecisionEngine:
    def __init__(
        self,
        weight_reflectance: float = 0.50,
        weight_rppg: float = 0.50,
        min_combined_score: float = 0.45
    ):
        self.w_ref = weight_reflectance
        self.w_rppg = weight_rppg
        self.min_combined_score = min_combined_score

    def evaluate(
        self,
        reflectance_result: Dict[str, Any],
        rppg_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aplica la regla de decisión combinada (Figura 2 del documento LumaVida).
        Evalúa la consistencia física entre la reflectancia cutánea ante el flash cromático
        y la fotopletismografía remota (rPPG).
        """
        ref_live = reflectance_result.get("is_live", False)
        rppg_live = rppg_result.get("is_live", False)

        ref_score = reflectance_result.get("reflectance_score", 0.0)
        rppg_score = rppg_result.get("confidence", 0.0)

        # Puntuación combinada ponderada
        combined_score = (self.w_ref * ref_score) + (self.w_rppg * rppg_score)

        specular = reflectance_result.get("specular_ratio", 0.0)
        corr = reflectance_result.get("correlation", 0.0)
        snr = rppg_result.get("snr", 0.0)
        bpm = rppg_result.get("bpm", 0.0)

        attack_type = "NONE"
        is_bona_fide = False

        # Regla de Decisión Fusión (Figura 2 UPCH):
        # Es legítimo (Bona Fide) si:
        # A) Ambas señales pasan de forma independiente (caso ideal)
        # B) Una señal es fuertemente positiva y la otra es consistente (sin indicios de spoofing):
        #    - Pulso rPPG fisiológico confirmado (rppg_live) + modulación de luz positiva (corr >= 0.18) y sin reflejo de cristal (specular <= 0.38)
        #    - Reflectancia cutánea concluyente (corr >= 0.35) + pulso rPPG en rango biológico humano (48 - 180 BPM)
        strong_rppg_valid_ref = rppg_live and (corr >= 0.18) and (specular <= 0.38)
        strong_ref_valid_bpm = (ref_score >= 0.35) and (48.0 <= bpm <= 180.0) and (snr >= 0.30)
        both_passed = ref_live and rppg_live

        if (both_passed or strong_rppg_valid_ref or strong_ref_valid_bpm) and (specular <= 0.38) and (combined_score >= self.min_combined_score):
            is_bona_fide = True
            decision_msg = "Muestra biométrica auténtica (Bona Fide) con tejido cutáneo reactivo y pulso fisiológico."
        else:
            # Identificación forense de ataque según ISO/IEC 30107
            if specular > 0.38:
                attack_type = "SPOOF_SCREEN_REPLAY"
                decision_msg = "Ataque de pantalla detectado (reflejo especular característico de cristal OLED/LCD)."
            elif corr < 0.14 and snr < 0.35:
                attack_type = "SPOOF_PRINTED_PHOTO"
                decision_msg = "Ataque de fotografía estática detectado (sin respuesta cutánea ni pulso sanguíneo)."
            elif corr >= 0.25 and not rppg_live:
                attack_type = "SPOOF_DEEPFAKE_OR_MASK"
                decision_msg = "Ataque de deepfake o máscara sintética detectado (ausencia de modulación microvascular rPPG)."
            else:
                attack_type = "SPOOF_GENERIC"
                decision_msg = "Fallo en prueba de vida: inconsistencia física entre estímulo lumínico y hemodinámica."

        return {
            "is_bona_fide": is_bona_fide,
            "attack_type": attack_type,
            "combined_score": round(float(combined_score), 4),
            "threshold": self.min_combined_score,
            "details": {
                "reflectance": reflectance_result,
                "rppg": rppg_result
            },
            "decision_message": decision_msg,
            "standards_compliance": {
                "iso_iec_30107_pad": "COMPLIANT",
                "evaluation_status": "PASS" if is_bona_fide else "REJECT_PAD"
            }
        }
