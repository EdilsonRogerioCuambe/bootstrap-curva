"""
matrix.py — Módulo 4: Montagem da matriz de fluxos C e do vetor de preços P.

A partir de todos os fluxos de caixa dos títulos e seus preços de mercado,
constrói o sistema linear C * d = P onde:
  - C[i][j] é o valor do fluxo do título i na data de pagamento j
  - d[j] é o fator de desconto para a data j (incógnita)
  - P[i] é o preço de mercado (PU) do título i

A ordenação crescente das datas garante que C seja triangular inferior,
tornando o sistema sempre solúvel por substituição progressiva.
"""

from datetime import date

import numpy as np

from src.bootstrap.calendar import count_business_days, to_years
from src.bootstrap.parser import BondRecord


def build_system(
    bonds: list[BondRecord],
    cashflows: dict[tuple[str, date], list[tuple[date, float]]],
    reference_date: date,
    holidays: list[str],
) -> tuple[np.ndarray, np.ndarray, list[date], list[int], list[float]]:
    """
    Monta o sistema linear C * d = P para bootstrapping da curva zero-cupom.

    Algoritmo:
      1. Coleta a união de todas as datas de pagamento de todos os títulos.
      2. Ordena essas datas cronologicamente (garante triangularidade de C).
      3. Para cada título (linha i) e cada data (coluna j):
           C[i][j] = valor do fluxo do título i na data j (0 se inexistente).
      4. P[i] = bond.pu (preço de mercado do título i).
      5. Calcula dias úteis (du) e prazo em anos para cada data de pagamento.

    Parameters
    ----------
    bonds : list[BondRecord]
        Lista de títulos (deve estar ordenada por vencimento crescente).
    cashflows : dict[tuple[str, date], list[tuple[date, float]]]
        Dicionário com chave (tipo, vencimento) e valor = lista (data, valor).
        Gerado por generate_all_cashflows().
    reference_date : date
        Data-base do cálculo (ponto zero da curva).
    holidays : list[str]
        Lista de feriados no formato 'YYYY-MM-DD'.

    Returns
    -------
    C : np.ndarray, shape (m, n)
        Matriz de fluxos de caixa. m = número de títulos, n = número de datas únicas.
    P : np.ndarray, shape (m,)
        Vetor de preços de mercado.
    payment_dates : list[date]
        Datas de pagamento únicas ordenadas cronologicamente.
    dus : list[int]
        Dias úteis entre reference_date e cada payment_date.
    years : list[float]
        Prazo em anos (DU / 252) para cada payment_date.

    Notes
    -----
    Para que o sistema C * d = P seja solúvel de forma única com np.linalg.solve,
    é necessário que C seja quadrada (m == n). Isso ocorre naturalmente quando
    cada título contribui com pelo menos uma data exclusiva (i.e., o conjunto de
    títulos cobre exatamente n datas distintas).
    """
    # 1. Coleta todas as datas únicas de pagamento (união)
    all_dates: set[date] = set()
    for cf_list in cashflows.values():
        for payment_date, _ in cf_list:
            all_dates.add(payment_date)

    # 2. Ordena cronologicamente
    payment_dates: list[date] = sorted(all_dates)
    n = len(payment_dates)
    m = len(bonds)

    # Mapeia cada data para seu índice na matriz
    date_index: dict[date, int] = {d: j for j, d in enumerate(payment_dates)}

    # 3. Monta a matriz C (zeros por padrão)
    C = np.zeros((m, n), dtype=float)
    for i, bond in enumerate(bonds):
        key = (bond.tipo, bond.vencimento)
        for payment_date, value in cashflows.get(key, []):
            j = date_index[payment_date]
            C[i, j] = value

    # 4. Monta o vetor P
    P = np.array([bond.pu for bond in bonds], dtype=float)

    # 5. Calcula DU e prazo em anos para cada data de pagamento
    dus: list[int] = [
        count_business_days(reference_date, d, holidays) for d in payment_dates
    ]
    years: list[float] = [to_years(du) for du in dus]

    return C, P, payment_dates, dus, years
