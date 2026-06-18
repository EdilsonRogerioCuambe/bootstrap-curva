"""
test_solver.py — Testes para o módulo solver.py.

Valida:
  - Resolução do sistema linear (fatores de desconto)
  - Conversão de fatores de desconto para taxas spot
  - Validação de re-precificação (Requisito R5)
"""

import numpy as np
import pytest

from src.bootstrap.solver import (
    discount_to_spot,
    solve_discount_factors,
    validate_repricing,
)

# ---------------------------------------------------------------------------
# Dados do gabarito ANBIMA 2026-06-01
# ---------------------------------------------------------------------------

from src.bootstrap.cashflows import NTNF_COUPON

CUPOM = NTNF_COUPON

# Matriz C do gabarito (3 títulos × 3 datas)
C_BENCHMARK = np.array(
    [
        [1000.0, 0.0, 0.0],
        [0.0, 1000.0, 0.0],
        [CUPOM, 0.0, 1000.0 + CUPOM],
    ]
)

# Vetor P do gabarito (PUs ANBIMA)
P_BENCHMARK = np.array([988.866252, 956.259296, 1019.143414])

# Fatores de desconto esperados
D_EXPECTED = np.array([0.988866, 0.956259, 0.925696])

# Taxas spot esperadas
S_EXPECTED = np.array([0.143798, 0.140034, 0.140498])

# Prazos em anos (DU/252)
YEARS = [21 / 252, 86 / 252, 148 / 252]


# ---------------------------------------------------------------------------
# Testes de solve_discount_factors
# ---------------------------------------------------------------------------


class TestSolveDiscountFactors:
    def test_output_shape(self):
        """Vetor de fatores de desconto deve ter mesmo comprimento que P."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert d.shape == P_BENCHMARK.shape

    def test_d0_matches_benchmark(self):
        """d[0] deve coincidir com gabarito ANBIMA para LTN jul/26."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert abs(d[0] - 0.988866) < 1e-5, f"d[0]={d[0]:.6f} ≠ 0.988866"

    def test_d1_matches_benchmark(self):
        """d[1] deve coincidir com gabarito ANBIMA para LTN out/26."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert abs(d[1] - 0.956259) < 1e-5, f"d[1]={d[1]:.6f} ≠ 0.956259"

    def test_d2_matches_benchmark(self):
        """d[2] deve coincidir com gabarito ANBIMA para NTN-F jan/27."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert abs(d[2] - 0.925696) < 1e-5, f"d[2]={d[2]:.6f} ≠ 0.925696"

    def test_discount_factors_are_positive(self):
        """Todos os fatores de desconto devem ser positivos."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert np.all(d > 0)

    def test_discount_factors_less_than_one(self):
        """Todos os fatores de desconto devem ser menores que 1."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert np.all(d < 1)

    def test_discount_factors_decreasing(self):
        """Fatores de desconto devem ser decrescentes (prazos crescentes)."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        assert d[0] > d[1] > d[2], (
            f"Fatores devem ser decrescentes: {d[0]:.6f} > {d[1]:.6f} > {d[2]:.6f}"
        )

    def test_trivial_system(self):
        """Sistema trivial (identidade) deve retornar P como d."""
        C = np.eye(3)
        P = np.array([0.9, 0.8, 0.7])
        d = solve_discount_factors(C, P)
        np.testing.assert_array_almost_equal(d, P)

    def test_singular_matrix_raises(self):
        """Matriz singular deve levantar LinAlgError."""
        C = np.zeros((2, 2))
        P = np.array([1.0, 1.0])
        with pytest.raises(np.linalg.LinAlgError):
            solve_discount_factors(C, P)


# ---------------------------------------------------------------------------
# Testes de discount_to_spot
# ---------------------------------------------------------------------------


class TestDiscountToSpot:
    def test_spot_ltn_jul(self):
        """Taxa spot para LTN jul/26 deve ser ≈ 14.3798% a.a."""
        d = np.array([0.988866])
        s = discount_to_spot(d, [21 / 252])
        assert abs(s[0] - 0.143798) < 1e-4, f"s[0]={s[0]:.6f} ≠ 0.143798"

    def test_spot_ltn_out(self):
        """Taxa spot para LTN out/26 deve ser ≈ 14.0034% a.a."""
        d = np.array([0.956259])
        s = discount_to_spot(d, [86 / 252])
        assert abs(s[0] - 0.140034) < 1e-4, f"s[0]={s[0]:.6f} ≠ 0.140034"

    def test_spot_ntnf_jan(self):
        """Taxa spot para NTN-F jan/27 deve ser ≈ 14.0498% a.a."""
        d = np.array([0.925696])
        s = discount_to_spot(d, [148 / 252])
        assert abs(s[0] - 0.140498) < 1e-4, f"s[0]={s[0]:.6f} ≠ 0.140498"

    def test_all_three_vertices(self):
        """Todos os três vértices devem bater com o gabarito ANBIMA."""
        d = D_EXPECTED
        s = discount_to_spot(d, YEARS)
        assert abs(s[0] - 0.143798) < 1e-4
        assert abs(s[1] - 0.140034) < 1e-4

    def test_discount_one_gives_zero_rate(self):
        """Fator de desconto = 1 para qualquer prazo → taxa spot = 0."""
        d = np.array([1.0, 1.0])
        s = discount_to_spot(d, [0.5, 1.0])
        np.testing.assert_array_almost_equal(s, [0.0, 0.0])

    def test_one_year_discount(self):
        """Para prazo = 1 ano: s = 1/d - 1 (capitalização simples equivale à composta)."""
        rate = 0.14
        d_val = 1.0 / (1 + rate)
        d = np.array([d_val])
        s = discount_to_spot(d, [1.0])
        assert abs(s[0] - rate) < 1e-10


# ---------------------------------------------------------------------------
# Testes de validate_repricing
# ---------------------------------------------------------------------------


class TestValidateRepricing:
    def test_perfect_repricing_returns_zero(self):
        """Re-precificação perfeita (d exato) deve retornar erro ≈ 0."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        error = validate_repricing(C_BENCHMARK, d, P_BENCHMARK)
        assert error < 1e-10

    def test_repricing_within_tolerance(self):
        """Erro abaixo de 1e-4 não deve levantar AssertionError."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        # Não deve levantar
        error = validate_repricing(C_BENCHMARK, d, P_BENCHMARK, tolerance=1e-4)
        assert isinstance(error, float)

    def test_repricing_exceeds_tolerance_raises(self):
        """Erro acima da tolerância deve levantar AssertionError."""
        d_errado = np.array([0.5, 0.5, 0.5])  # Fatores muito errados
        with pytest.raises(AssertionError, match="Repricing error too large"):
            validate_repricing(C_BENCHMARK, d_errado, P_BENCHMARK)

    def test_returns_float(self):
        """validate_repricing deve retornar um float."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        result = validate_repricing(C_BENCHMARK, d, P_BENCHMARK)
        assert isinstance(result, float)

    def test_r5_requirement(self):
        """Requisito R5: erro de re-precificação deve ser < 1e-4."""
        d = solve_discount_factors(C_BENCHMARK, P_BENCHMARK)
        error = validate_repricing(C_BENCHMARK, d, P_BENCHMARK, tolerance=1e-4)
        assert error < 1e-4
