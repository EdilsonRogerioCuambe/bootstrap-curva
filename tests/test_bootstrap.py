"""
test_bootstrap.py — Testes de integração para o pipeline completo.

Usa dados hardcoded do gabarito ANBIMA (2026-06-01) para validar o pipeline
end-to-end sem depender de arquivos externos.

Requisito R5: erro de re-precificação < 1e-4.
"""

from datetime import date

import numpy as np
import pytest

from src.bootstrap.calendar import count_business_days
from src.bootstrap.cashflows import NTNF_COUPON
from src.bootstrap.matrix import build_system
from src.bootstrap.cashflows import generate_all_cashflows
from src.bootstrap.parser import BondRecord
from src.bootstrap.solver import (
    discount_to_spot,
    solve_discount_factors,
    validate_repricing,
)

# ---------------------------------------------------------------------------
# Dados do gabarito ANBIMA 2026-06-01
# ---------------------------------------------------------------------------

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

CUPOM = NTNF_COUPON  # 1000 * ((1.10)^0.5 - 1) ≈ 48.8088

# Matriz C do gabarito (exatamente como descrita no desafio)
C_GABARITO = np.array(
    [
        [1000.0, 0.0, 0.0],
        [0.0, 1000.0, 0.0],
        [CUPOM, 0.0, 1000.0 + CUPOM],
    ]
)

# Preços de mercado ANBIMA
P_GABARITO = np.array([988.866252, 956.259296, 1019.143414])

# Fatores de desconto esperados
D_ESPERADO = np.array([0.988866, 0.956259, 0.925696])


# ---------------------------------------------------------------------------
# Testes de integração do pipeline (usando matrix + solver diretamente)
# ---------------------------------------------------------------------------


class TestFullPipelineRepricing:
    """Valida o pipeline completo com dados do gabarito ANBIMA."""

    def test_full_pipeline_repricing(self):
        """
        Teste de integração: valida que a curva gerada re-precifica
        todos os títulos com erro < 1e-4 (Requisito R5).
        Usa dados do exemplo ANBIMA 2026-06-01.
        """
        d = solve_discount_factors(C_GABARITO, P_GABARITO)
        error = validate_repricing(C_GABARITO, d, P_GABARITO)

        assert error < 1e-4
        assert abs(d[0] - 0.988866) < 1e-5
        assert abs(d[1] - 0.956259) < 1e-5
        assert abs(d[2] - 0.925696) < 1e-5

    def test_spot_rates_match_anbima(self):
        """Taxas spot devem coincidir com Tx. Indicativa da ANBIMA para LTNs."""
        d = np.array([0.988866, 0.956259, 0.925696])
        years = [21 / 252, 86 / 252, 148 / 252]
        s = discount_to_spot(d, years)

        assert abs(s[0] - 0.143798) < 1e-4, f"LTN jul/26: s={s[0]:.6f} ≠ 0.143798"
        assert abs(s[1] - 0.140034) < 1e-4, f"LTN out/26: s={s[1]:.6f} ≠ 0.140034"

    def test_discount_factors_ordered(self):
        """Fatores de desconto devem ser decrescentes (prazos crescentes)."""
        d = np.array([0.988866, 0.956259, 0.925696])
        assert d[0] > d[1] > d[2]

    def test_business_days_match_anbima_benchmark(self):
        """DUs calculados devem bater exatamente com o gabarito ANBIMA."""
        assert count_business_days(BASE, date(2026, 7, 1), HOLIDAYS) == 21
        assert count_business_days(BASE, date(2026, 10, 1), HOLIDAYS) == 86
        assert count_business_days(BASE, date(2027, 1, 1), HOLIDAYS) == 148


# ---------------------------------------------------------------------------
# Testes end-to-end usando build_system + solver
# ---------------------------------------------------------------------------


class TestEndToEndWithMatrix:
    """Testa o pipeline completo usando os módulos matrix e solver."""

    def setup_method(self):
        """Configura os títulos do gabarito ANBIMA."""
        self.bonds = [
            BondRecord(
                tipo="LTN",
                vencimento=date(2026, 7, 1),
                pu=988.866252,
                tx_indicativa=0.143798,
            ),
            BondRecord(
                tipo="LTN",
                vencimento=date(2026, 10, 1),
                pu=956.259296,
                tx_indicativa=0.140034,
            ),
            BondRecord(
                tipo="NTN-F",
                vencimento=date(2027, 1, 1),
                pu=1019.143414,
                tx_indicativa=0.140521,
            ),
        ]

    def test_matrix_matches_gabarito(self):
        """Matriz C gerada pelo pipeline deve coincidir com o gabarito."""
        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, _, _, _ = build_system(self.bonds, cashflows, BASE, HOLIDAYS)

        np.testing.assert_array_almost_equal(C, C_GABARITO, decimal=6)
        np.testing.assert_array_almost_equal(P, P_GABARITO, decimal=6)

    def test_end_to_end_discount_factors(self):
        """Pipeline completo deve produzir fatores de desconto do gabarito."""
        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, _, _, years = build_system(self.bonds, cashflows, BASE, HOLIDAYS)
        d = solve_discount_factors(C, P)

        assert abs(d[0] - 0.988866) < 1e-5
        assert abs(d[1] - 0.956259) < 1e-5
        assert abs(d[2] - 0.925696) < 1e-5

    def test_end_to_end_spot_rates(self):
        """Pipeline completo deve produzir taxas spot do gabarito."""
        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, _, _, years = build_system(self.bonds, cashflows, BASE, HOLIDAYS)
        d = solve_discount_factors(C, P)
        s = discount_to_spot(d, years)

        assert abs(s[0] - 0.143798) < 1e-4
        assert abs(s[1] - 0.140034) < 1e-4

    def test_end_to_end_r5_repricing(self):
        """Pipeline completo deve satisfazer o Requisito R5 (erro < 1e-4)."""
        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, _, _, years = build_system(self.bonds, cashflows, BASE, HOLIDAYS)
        d = solve_discount_factors(C, P)
        error = validate_repricing(C, d, P, tolerance=1e-4)

        assert error < 1e-4

    def test_spot_rates_in_reasonable_range(self):
        """Taxas spot devem estar em faixa razoável para o mercado brasileiro."""
        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, _, _, years = build_system(self.bonds, cashflows, BASE, HOLIDAYS)
        d = solve_discount_factors(C, P)
        s = discount_to_spot(d, years)

        # Taxas entre 5% e 30% (faixa histórica razoável para o Brasil)
        assert np.all(s > 0.05)
        assert np.all(s < 0.30)

    def test_output_dict_structure(self):
        """Testa a estrutura do dicionário de saída do pipeline."""
        from src.bootstrap.cashflows import FACE_VALUE

        cashflows = generate_all_cashflows(self.bonds, BASE)
        C, P, payment_dates, dus, years = build_system(
            self.bonds, cashflows, BASE, HOLIDAYS
        )
        d = solve_discount_factors(C, P)
        error = validate_repricing(C, d, P)
        s = discount_to_spot(d, years)

        result = {
            "data_base": BASE.isoformat(),
            "erro_reprecificacao": float(error),
            "curva": [
                {
                    "data": payment_dates[j].isoformat(),
                    "du": dus[j],
                    "prazo_anos": round(years[j], 6),
                    "fator_desconto": round(float(d[j]), 6),
                    "taxa_spot": round(float(s[j]), 6),
                }
                for j in range(len(payment_dates))
            ],
        }

        assert result["data_base"] == "2026-06-01"
        assert result["erro_reprecificacao"] < 1e-4
        assert len(result["curva"]) == 3
        assert all("data" in v for v in result["curva"])
        assert all("du" in v for v in result["curva"])
        assert all("fator_desconto" in v for v in result["curva"])
        assert all("taxa_spot" in v for v in result["curva"])
