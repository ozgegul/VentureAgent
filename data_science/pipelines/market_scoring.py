"""Basit girişim skorlama yardımcıları.

Bu dosya data science tarafı için başlangıç noktasıdır. İleride gerçek veri,
anket sonuçları veya pazar metrikleri geldikçe buradaki kurallar model ya da
istatistiksel analizlerle değiştirilebilir.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupSignal:
    problem_severity: int
    target_audience_clarity: int
    competition_intensity: int
    monetization_clarity: int


@dataclass(frozen=True)
class VentureScore:
    score: float
    risk_level: str
    readiness_label: str
    recommendations: list[str]


def normalize_score(value: int) -> int:
    """1-5 aralığındaki kullanıcı skorunu güvenli şekilde normalize eder."""
    return max(1, min(5, value))


def calculate_market_readiness(signal: StartupSignal) -> float:
    """Girişim fikri için 0-100 arasında ilk pazar hazırlık skoru üretir."""
    problem = normalize_score(signal.problem_severity) * 0.35
    audience = normalize_score(signal.target_audience_clarity) * 0.25
    monetization = normalize_score(signal.monetization_clarity) * 0.25
    competition = (6 - normalize_score(signal.competition_intensity)) * 0.15

    return round(((problem + audience + monetization + competition) / 5) * 100, 2)


def classify_risk(score: float) -> str:
    """Skora göre yalın risk sınıfı üretir."""
    if score >= 75:
        return "Düşük risk"
    if score >= 55:
        return "Orta risk"
    return "Yüksek risk"


def classify_readiness(score: float) -> str:
    """Skora göre fikrin hazırlık seviyesini etiketler."""
    if score >= 80:
        return "Yatırımcı görüşmesine yakın"
    if score >= 65:
        return "MVP planlamaya hazır"
    if score >= 45:
        return "Doğrulama aşamasında"
    return "Problem-keşif aşamasında"


def build_recommendations(signal: StartupSignal) -> list[str]:
    """Zayıf sinyallere göre aksiyon önerileri üretir."""
    recommendations = []

    if normalize_score(signal.problem_severity) <= 3:
        recommendations.append("Problemin aciliyetini kullanıcı görüşmeleriyle daha net kanıtla.")
    if normalize_score(signal.target_audience_clarity) <= 3:
        recommendations.append("Hedef kitleyi daha dar bir erken kullanıcı segmentine indir.")
    if normalize_score(signal.competition_intensity) >= 4:
        recommendations.append("Rakiplerden ayrışan tek güçlü vaadini daha görünür yap.")
    if normalize_score(signal.monetization_clarity) <= 3:
        recommendations.append("İlk gelir modelini ve ödeme motivasyonunu test edecek küçük bir deney tasarla.")

    if not recommendations:
        recommendations.append("Sinyaller güçlü görünüyor; sonraki adım olarak MVP kapsamını daraltıp test planı oluştur.")

    return recommendations


def build_venture_score(signal: StartupSignal) -> VentureScore:
    """Tüm data science skor çıktısını tek nesnede toplar."""
    score = calculate_market_readiness(signal)
    return VentureScore(
        score=score,
        risk_level=classify_risk(score),
        readiness_label=classify_readiness(score),
        recommendations=build_recommendations(signal),
    )
