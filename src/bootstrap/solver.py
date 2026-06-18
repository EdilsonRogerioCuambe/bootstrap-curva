"""
solver.py — Módulo 5: Resolução do sistema C*d=P e conversão para taxas spot.

Usa numpy.linalg.solve (decomposição LU via LAPACK) para resolver o sistema
linear e obter os fatores de desconto. Em seguida, converte cada fator de
desconto em taxa spot anual pela fórmula:

    s_i = d_i^(-1/p_i) - 1

onde p_i é o prazo em anos (DU / 252).

Inclui validação obrigatória de re-precificação (Requisito R5): verifica que
a curva calculada reproduz os preços de mercado com tolerância < 1e-4.
"""

import numpy as np


def solve_discount_factors(C: np.ndarray, P: np.ndarray) -> np.ndarray:
    """
    Resolve o sistema linear C * d = P para obter os fatores de desconto.

    Usa numpy.linalg.solve, que internamente aplica decomposição LU (LAPACK
    dgesv). Para matrizes triangulares inferiores (caso típico do bootstrap),
    isso é equivalente à substituição progressiva (forward substitution),
    porém com maior estabilidade numérica.

    Parameters
    ----------
    C : np.ndarray, shape (n, n)
        Matriz de fluxos de caixa (deve ser quadrada e inversível).
    P : np.ndarray, shape (n,)
        Vetor de preços de mercado (PU ANBIMA).

    Returns
    -------
    np.ndarray, shape (n,)
        Vetor d de fatores de desconto para cada vértice da curva.

    Raises
    ------
    numpy.linalg.LinAlgError
        Se a matriz C for singular (sistema sem solução única).
    """
    return np.linalg.solve(C, P)


def discount_to_spot(
    d: np.ndarray,
    years: list[float],
) -> np.ndarray:
    """
    Converte fatores de desconto em taxas spot anuais (capitalização composta,
    base 252 dias úteis).

    Fórmula: s_i = d_i^(-1/p_i) - 1

    Onde:
      d_i  = fator de desconto para o vértice i
      p_i  = prazo em anos (DU_i / 252)
      s_i  = taxa spot anual para o vértice i

    Parameters
    ----------
    d : np.ndarray, shape (n,)
        Vetor de fatores de desconto (valores entre 0 e 1).
    years : list[float]
        Lista de prazos em anos correspondentes a cada fator de desconto.

    Returns
    -------
    np.ndarray, shape (n,)
        Vetor de taxas spot anuais em decimal (ex: 0.143798 = 14.3798% a.a.).

    Examples
    --------
    >>> import numpy as np
    >>> d = np.array([0.988866])
    >>> discount_to_spot(d, [0.0833])
    array([0.14379...])
    """
    p = np.array(years, dtype=float)
    return d ** (-1.0 / p) - 1.0


def validate_repricing(
    C: np.ndarray,
    d: np.ndarray,
    P: np.ndarray,
    tolerance: float = 1e-4,
) -> float:
    """
    Valida a curva calculada re-precificando todos os títulos (Requisito R5).

    Re-precifica cada título como P_calc_i = soma(C[i,j] * d[j]) = (C @ d)[i]
    e compara com o preço de mercado P[i]. Levanta AssertionError se o erro
    máximo absoluto superar a tolerância.

    Parameters
    ----------
    C : np.ndarray, shape (m, n)
        Matriz de fluxos de caixa.
    d : np.ndarray, shape (n,)
        Vetor de fatores de desconto calculados.
    P : np.ndarray, shape (m,)
        Vetor de preços de mercado (PU ANBIMA).
    tolerance : float, optional
        Tolerância máxima para o erro de re-precificação. Default: 1e-4.

    Returns
    -------
    float
        Erro máximo absoluto de re-precificação entre todos os títulos.

    Raises
    ------
    AssertionError
        Se qualquer erro de re-precificação superar a tolerância.

    Examples
    --------
    >>> import numpy as np
    >>> C = np.array([[1000.0]])
    >>> d = np.array([0.988866])
    >>> P = np.array([988.866])
    >>> validate_repricing(C, d, P)  # doctest: +ELLIPSIS
    0.0...
    """
    P_calc = C @ d
    max_error = float(np.max(np.abs(P_calc - P)))
    assert max_error < tolerance, (
        f"Repricing error too large: {max_error:.2e} "
        f"(tolerance: {tolerance:.0e})"
    )
    return max_error
