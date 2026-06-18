"""
test_calendar.py — Testes para o módulo calendar.py.

Valida:
  - Contagem de dias úteis bate com o gabarito ANBIMA (data-base 2026-06-01)
  - Conversão de DU para anos (base 252)
"""

from datetime import date

import pytest

from src.bootstrap.calendar import count_business_days, to_years


# Feriados ANBIMA relevantes para o período jun/2026–jan/2027
HOLIDAYS = [
    "2026-06-11",  # Corpus Christi
    "2026-09-07",  # Independência
    "2026-10-12",  # N. Sra. Aparecida
    "2026-11-02",  # Finados
    "2026-11-15",  # Proclamação da República
    "2026-11-20",  # Consciência Negra
    "2026-12-25",  # Natal
    "2027-01-01",  # Ano Novo
]

BASE = date(2026, 6, 1)


class TestCountBusinessDays:
    """Testes de contagem de dias úteis contra gabarito ANBIMA."""

    def test_du_jul_2026(self):
        """2026-06-01 → 2026-07-01 deve ser 21 DU (gabarito ANBIMA)."""
        result = count_business_days(BASE, date(2026, 7, 1), HOLIDAYS)
        assert result == 21, f"Esperado 21 DU, obtido {result}"

    def test_du_out_2026(self):
        """2026-06-01 → 2026-10-01 deve ser 86 DU (gabarito ANBIMA)."""
        result = count_business_days(BASE, date(2026, 10, 1), HOLIDAYS)
        assert result == 86, f"Esperado 86 DU, obtido {result}"

    def test_du_jan_2027(self):
        """2026-06-01 → 2027-01-01 deve ser 148 DU (gabarito ANBIMA)."""
        result = count_business_days(BASE, date(2027, 1, 1), HOLIDAYS)
        assert result == 148, f"Esperado 148 DU, obtido {result}"

    def test_same_day_returns_zero(self):
        """Intervalo [d, d) deve retornar 0."""
        result = count_business_days(BASE, BASE, HOLIDAYS)
        assert result == 0

    def test_weekend_excluded(self):
        """Fim de semana não conta como dia útil."""
        # 2026-06-01 (seg) → 2026-06-08 (seg) = 5 DU (sem feriados no período)
        result = count_business_days(BASE, date(2026, 6, 8), [])
        assert result == 5

    def test_holiday_excluded(self):
        """Feriado (Corpus Christi 2026-06-11) não conta como dia útil."""
        # Sem feriados: 2026-06-01 → 2026-06-12 = 9 DU
        result_no_holiday = count_business_days(
            BASE, date(2026, 6, 12), []
        )
        # Com feriado 2026-06-11: deve ser 8 DU
        result_with_holiday = count_business_days(
            BASE, date(2026, 6, 12), ["2026-06-11"]
        )
        assert result_no_holiday == 9
        assert result_with_holiday == 8
        assert result_with_holiday == result_no_holiday - 1


class TestToYears:
    """Testes de conversão de DU para anos (base 252)."""

    def test_21_du(self):
        """21 DU deve corresponder a ~0.0833 anos."""
        result = to_years(21)
        assert abs(result - 21 / 252) < 1e-10

    def test_252_du(self):
        """252 DU deve corresponder a exatamente 1 ano."""
        assert to_years(252) == 1.0

    def test_zero_du(self):
        """0 DU deve resultar em 0.0 anos."""
        assert to_years(0) == 0.0

    def test_half_year(self):
        """126 DU deve corresponder a 0.5 anos."""
        assert to_years(126) == 0.5

    def test_86_du(self):
        """86 DU / 252 ≈ 0.3413 anos (vértice LTN out/26)."""
        result = to_years(86)
        assert abs(result - 86 / 252) < 1e-10

    def test_148_du(self):
        """148 DU / 252 ≈ 0.5873 anos (vértice NTN-F jan/27)."""
        result = to_years(148)
        assert abs(result - 148 / 252) < 1e-10
