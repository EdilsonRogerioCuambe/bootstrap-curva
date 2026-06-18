"""
test_cashflows.py — Testes para o módulo cashflows.py.

Valida:
  - LTN gera exatamente 1 fluxo de R$ 1.000
  - NTN-F gera fluxos corretos (cupom composto ≈ 48.8088, não 50.0)
  - Fluxos passados/iguais à data-base são excluídos
"""

import math
from datetime import date

import pytest

from src.bootstrap.cashflows import (
    FACE_VALUE,
    NTNF_COUPON,
    generate_all_cashflows,
    generate_cashflows,
)
from src.bootstrap.parser import BondRecord


# ---------------------------------------------------------------------------
# Fixtures de títulos para os testes
# ---------------------------------------------------------------------------

BASE = date(2026, 6, 1)


def make_ltn(vencimento: date) -> BondRecord:
    return BondRecord(tipo="LTN", vencimento=vencimento, pu=0.0, tx_indicativa=0.0)


def make_ntnf(vencimento: date) -> BondRecord:
    return BondRecord(tipo="NTN-F", vencimento=vencimento, pu=0.0, tx_indicativa=0.0)


# ---------------------------------------------------------------------------
# Testes de constantes
# ---------------------------------------------------------------------------


class TestConstants:
    def test_face_value(self):
        """Valor de face deve ser R$ 1.000."""
        assert FACE_VALUE == 1000.0

    def test_ntnf_coupon_formula(self):
        """Cupom NTN-F = 1000 * ((1.10)^0.5 - 1) ≈ 48.8088 (não 50.0)."""
        expected = 1000.0 * ((1.10**0.5) - 1)
        assert abs(NTNF_COUPON - expected) < 1e-10

    def test_ntnf_coupon_is_not_50(self):
        """Cupom NTN-F NÃO deve ser 10%/2 = 50.0 (capitalização simples)."""
        assert NTNF_COUPON != 50.0

    def test_ntnf_coupon_value(self):
        """Cupom NTN-F ≈ 48.8088."""
        assert abs(NTNF_COUPON - 48.8088) < 1e-3


# ---------------------------------------------------------------------------
# Testes para LTN
# ---------------------------------------------------------------------------


class TestLTNCashflows:
    def test_single_cashflow(self):
        """LTN deve gerar exatamente 1 fluxo."""
        bond = make_ltn(date(2026, 7, 1))
        cfs = generate_cashflows(bond, BASE)
        assert len(cfs) == 1

    def test_cashflow_date_is_maturity(self):
        """O fluxo da LTN deve ocorrer na data de vencimento."""
        venc = date(2026, 7, 1)
        bond = make_ltn(venc)
        cfs = generate_cashflows(bond, BASE)
        assert cfs[0][0] == venc

    def test_cashflow_value_is_face(self):
        """O valor do fluxo da LTN deve ser o valor de face (R$ 1.000)."""
        bond = make_ltn(date(2026, 7, 1))
        cfs = generate_cashflows(bond, BASE)
        assert cfs[0][1] == 1000.0

    def test_expired_ltn_returns_empty(self):
        """LTN com vencimento <= data-base não deve gerar fluxos."""
        bond = make_ltn(date(2026, 5, 1))  # Vencido
        cfs = generate_cashflows(bond, BASE)
        assert cfs == []

    def test_maturity_equals_base_returns_empty(self):
        """LTN com vencimento == data-base não gera fluxos (convenção > base)."""
        bond = make_ltn(BASE)
        cfs = generate_cashflows(bond, BASE)
        assert cfs == []


# ---------------------------------------------------------------------------
# Testes para NTN-F
# ---------------------------------------------------------------------------


class TestNTNFCashflows:
    def test_two_cashflows_for_challenge_case(self):
        """NTN-F jan/2027 a partir de jun/2026 deve gerar 2 fluxos:
        cupom em 2026-07-01 e cupom+principal em 2027-01-01."""
        bond = make_ntnf(date(2027, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        assert len(cfs) == 2

    def test_first_cashflow_is_coupon_jul(self):
        """Primeiro fluxo da NTN-F deve ser o cupom em 01/jul/2026."""
        bond = make_ntnf(date(2027, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        assert cfs[0][0] == date(2026, 7, 1)
        assert abs(cfs[0][1] - NTNF_COUPON) < 1e-10

    def test_last_cashflow_is_principal_plus_coupon(self):
        """Último fluxo da NTN-F deve ser cupom + principal no vencimento."""
        bond = make_ntnf(date(2027, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        assert cfs[-1][0] == date(2027, 1, 1)
        assert abs(cfs[-1][1] - (FACE_VALUE + NTNF_COUPON)) < 1e-10

    def test_cashflows_are_chronological(self):
        """Fluxos devem estar em ordem cronológica."""
        bond = make_ntnf(date(2028, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        dates = [cf[0] for cf in cfs]
        assert dates == sorted(dates)

    def test_ntnf_with_multiple_coupons(self):
        """NTN-F com vencimento em jan/2028 deve gerar 4 fluxos a partir de jun/2026:
        jul/2026, jan/2027, jul/2027, jan/2028."""
        bond = make_ntnf(date(2028, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        assert len(cfs) == 4
        dates = [cf[0] for cf in cfs]
        assert date(2026, 7, 1) in dates
        assert date(2027, 1, 1) in dates
        assert date(2027, 7, 1) in dates
        assert date(2028, 1, 1) in dates

    def test_intermediate_coupons_value(self):
        """Cupons intermediários devem ser NTNF_COUPON (não principal)."""
        bond = make_ntnf(date(2028, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        for payment_date, value in cfs[:-1]:  # Todos exceto o último
            assert abs(value - NTNF_COUPON) < 1e-10, (
                f"Cupom intermediário em {payment_date} deveria ser "
                f"{NTNF_COUPON:.4f}, obtido {value:.4f}"
            )

    def test_expired_ntnf_returns_empty(self):
        """NTN-F vencida não deve gerar fluxos."""
        bond = make_ntnf(date(2025, 1, 1))
        cfs = generate_cashflows(bond, BASE)
        assert cfs == []


# ---------------------------------------------------------------------------
# Testes para generate_all_cashflows
# ---------------------------------------------------------------------------


class TestGenerateAllCashflows:
    def test_keys_are_tipo_vencimento(self):
        """Chaves do dicionário devem ser (tipo, vencimento)."""
        bonds = [
            make_ltn(date(2026, 7, 1)),
            make_ntnf(date(2027, 1, 1)),
        ]
        all_cf = generate_all_cashflows(bonds, BASE)
        assert ("LTN", date(2026, 7, 1)) in all_cf
        assert ("NTN-F", date(2027, 1, 1)) in all_cf

    def test_all_bonds_present(self):
        """Todos os títulos devem ter entrada no dicionário."""
        bonds = [
            make_ltn(date(2026, 7, 1)),
            make_ltn(date(2026, 10, 1)),
            make_ntnf(date(2027, 1, 1)),
        ]
        all_cf = generate_all_cashflows(bonds, BASE)
        assert len(all_cf) == 3

    def test_unsupported_type_raises(self):
        """Tipo de título não suportado deve levantar ValueError."""
        bond = BondRecord(
            tipo="LFT", vencimento=date(2027, 1, 1), pu=0.0, tx_indicativa=0.0
        )
        with pytest.raises(ValueError, match="não suportado"):
            generate_cashflows(bond, BASE)
