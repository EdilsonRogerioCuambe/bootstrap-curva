"""
test_matrix.py — Testes para o módulo matrix.py.

Valida:
  - Dimensões corretas da matriz C e vetor P
  - Preenchimento correto dos fluxos na matriz
  - Datas de pagamento ordenadas cronologicamente
  - DUs e prazos corretos para o gabarito ANBIMA
"""

from datetime import date

import numpy as np
import pytest

from src.bootstrap.cashflows import FACE_VALUE, NTNF_COUPON, generate_all_cashflows
from src.bootstrap.matrix import build_system
from src.bootstrap.parser import BondRecord


# ---------------------------------------------------------------------------
# Dados do gabarito ANBIMA 2026-06-01
# ---------------------------------------------------------------------------

BASE = date(2026, 6, 1)

HOLIDAYS = [
    "2026-06-11",
    "2026-09-07",
    "2026-10-12",
    "2026-11-02",
    "2026-11-15",
    "2026-11-20",
    "2026-12-25",
    "2027-01-01",
]

# Títulos do gabarito ANBIMA
LTN_JUL = BondRecord(
    tipo="LTN",
    vencimento=date(2026, 7, 1),
    pu=988.866252,
    tx_indicativa=0.143798,
)
LTN_OUT = BondRecord(
    tipo="LTN",
    vencimento=date(2026, 10, 1),
    pu=956.259296,
    tx_indicativa=0.140034,
)
NTNF_JAN = BondRecord(
    tipo="NTN-F",
    vencimento=date(2027, 1, 1),
    pu=1019.143414,
    tx_indicativa=0.140521,
)

BONDS = [LTN_JUL, LTN_OUT, NTNF_JAN]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def build_test_system():
    """Monta o sistema com os dados do gabarito ANBIMA."""
    cashflows = generate_all_cashflows(BONDS, BASE)
    return build_system(BONDS, cashflows, BASE, HOLIDAYS)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestBuildSystem:
    def test_output_shape_square(self):
        """Matriz C deve ser quadrada (m == n) para o sistema ser solúvel."""
        C, P, payment_dates, dus, years = build_test_system()
        assert C.shape[0] == C.shape[1], (
            f"C deve ser quadrada, obtido shape {C.shape}"
        )

    def test_matrix_shape_3x3(self):
        """Para 3 títulos e 3 datas únicas, C deve ser 3×3."""
        C, P, payment_dates, dus, years = build_test_system()
        assert C.shape == (3, 3)

    def test_price_vector_shape(self):
        """Vetor P deve ter comprimento igual ao número de títulos."""
        C, P, payment_dates, dus, years = build_test_system()
        assert P.shape == (3,)

    def test_price_vector_values(self):
        """Vetor P deve conter os PUs do gabarito ANBIMA."""
        C, P, payment_dates, dus, years = build_test_system()
        assert abs(P[0] - 988.866252) < 1e-6
        assert abs(P[1] - 956.259296) < 1e-6
        assert abs(P[2] - 1019.143414) < 1e-6

    def test_payment_dates_ordered(self):
        """Datas de pagamento devem estar em ordem cronológica."""
        C, P, payment_dates, dus, years = build_test_system()
        assert payment_dates == sorted(payment_dates)

    def test_payment_dates_content(self):
        """Datas de pagamento devem conter as 3 datas do gabarito."""
        C, P, payment_dates, dus, years = build_test_system()
        assert date(2026, 7, 1) in payment_dates
        assert date(2026, 10, 1) in payment_dates
        assert date(2027, 1, 1) in payment_dates

    def test_dus_match_anbima_benchmark(self):
        """DUs calculados devem bater com o gabarito ANBIMA."""
        C, P, payment_dates, dus, years = build_test_system()
        du_by_date = dict(zip(payment_dates, dus))
        assert du_by_date[date(2026, 7, 1)] == 21
        assert du_by_date[date(2026, 10, 1)] == 86
        assert du_by_date[date(2027, 1, 1)] == 148

    def test_years_match_anbima_benchmark(self):
        """Prazos em anos devem corresponder ao gabarito ANBIMA."""
        C, P, payment_dates, dus, years = build_test_system()
        years_by_date = dict(zip(payment_dates, years))
        assert abs(years_by_date[date(2026, 7, 1)] - 21 / 252) < 1e-10
        assert abs(years_by_date[date(2026, 10, 1)] - 86 / 252) < 1e-10
        assert abs(years_by_date[date(2027, 1, 1)] - 148 / 252) < 1e-10

    def test_ltn_jul_row(self):
        """Linha da LTN jul/26: único fluxo de 1000 na coluna 0."""
        C, P, payment_dates, dus, years = build_test_system()
        row = C[0]  # LTN jul/26 (ordenada por vencimento)
        assert abs(row[0] - FACE_VALUE) < 1e-10  # Fluxo em jul/26
        assert row[1] == 0.0                      # Sem fluxo em out/26
        assert row[2] == 0.0                      # Sem fluxo em jan/27

    def test_ltn_out_row(self):
        """Linha da LTN out/26: único fluxo de 1000 na coluna 1."""
        C, P, payment_dates, dus, years = build_test_system()
        row = C[1]  # LTN out/26
        assert row[0] == 0.0                      # Sem fluxo em jul/26
        assert abs(row[1] - FACE_VALUE) < 1e-10  # Fluxo em out/26
        assert row[2] == 0.0                      # Sem fluxo em jan/27

    def test_ntnf_row(self):
        """Linha da NTN-F jan/27: cupom em jul/26, cupom+principal em jan/27."""
        C, P, payment_dates, dus, years = build_test_system()
        row = C[2]  # NTN-F jan/27
        assert abs(row[0] - NTNF_COUPON) < 1e-10          # Cupom em jul/26
        assert row[1] == 0.0                               # Sem fluxo em out/26
        assert abs(row[2] - (FACE_VALUE + NTNF_COUPON)) < 1e-10  # Principal + cupom em jan/27

    def test_matrix_lower_triangular(self):
        """Matriz C deve ser triangular inferior (zeros acima da diagonal)."""
        C, P, payment_dates, dus, years = build_test_system()
        upper_triangle = np.triu(C, k=1)  # Acima da diagonal principal
        assert np.all(upper_triangle == 0), (
            "Matriz C não é triangular inferior. "
            f"Elementos não-zero acima da diagonal: {np.nonzero(upper_triangle)}"
        )
