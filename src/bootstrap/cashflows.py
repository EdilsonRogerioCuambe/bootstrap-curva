"""
cashflows.py — Módulo 3: Geração de fluxos de caixa por título.

Dado um BondRecord e uma data-base, retorna a lista de (data, valor) de todos
os pagamentos futuros do título.

Tipos suportados:
  - LTN  : zero-cupom — um único fluxo de R$ 1.000 no vencimento
  - NTN-F: cupons semestrais em 01/jan e 01/jul, mais principal no vencimento

Cálculo do cupom NTN-F (capitalização composta semestral, taxa de 10% a.a.):
  cupom = 1000 × ((1.10)^(1/2) − 1) ≈ 48.8088
  NÃO usar 10%/2 = 50 (seria capitalização simples, incorreto para NTN-F).
"""

from datetime import date
import calendar as _cal

from src.bootstrap.parser import BondRecord


def _subtract_months(d: date, months: int) -> date:
    """
    Subtrai *months* meses de uma data, usando apenas a biblioteca padrão.

    Mantém o dia do mês original; se o dia não existir no mês resultante,
    usa o último dia desse mês.

    Parameters
    ----------
    d : date
        Data original.
    months : int
        Número de meses a subtrair (deve ser positivo).

    Returns
    -------
    date
        Nova data com *months* meses a menos.
    """
    total_months = d.year * 12 + (d.month - 1) - months
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(d.day, _cal.monthrange(year, month)[1])
    return date(year, month, day)


# Valor de face do Tesouro Nacional (R$)
FACE_VALUE: float = 1000.0

# Cupom semestral da NTN-F: capitalização composta (taxa anual 10%, base semestral)
# Fórmula: 1000 × ((1.10)^(0.5) − 1) = 48.808848170...
NTNF_COUPON: float = FACE_VALUE * ((1.10**0.5) - 1)


def generate_cashflows(
    bond: BondRecord,
    reference_date: date,
) -> list[tuple[date, float]]:
    """
    Gera a lista de fluxos de caixa futuros para um título dado.

    Retorna apenas fluxos com data de pagamento estritamente maior que
    reference_date (fluxos passados ou do próprio dia são ignorados).

    Parameters
    ----------
    bond : BondRecord
        Título para o qual gerar os fluxos.
    reference_date : date
        Data-base do cálculo (data de referência de precificação).

    Returns
    -------
    list[tuple[date, float]]
        Lista de (data_pagamento, valor) ordenada cronologicamente.

    Raises
    ------
    ValueError
        Se o tipo do título não for suportado.
    """
    if bond.tipo == "LTN":
        return _generate_ltn_cashflows(bond, reference_date)
    elif bond.tipo == "NTN-F":
        return _generate_ntnf_cashflows(bond, reference_date)
    else:
        raise ValueError(
            f"Tipo de título não suportado: '{bond.tipo}'. "
            "Use 'LTN' ou 'NTN-F'."
        )


def _generate_ltn_cashflows(
    bond: BondRecord,
    reference_date: date,
) -> list[tuple[date, float]]:
    """
    Gera fluxos para LTN (zero-cupom).

    LTN paga apenas o valor de face (R$ 1.000) no vencimento.

    Parameters
    ----------
    bond : BondRecord
        Título LTN.
    reference_date : date
        Data-base do cálculo.

    Returns
    -------
    list[tuple[date, float]]
        Lista com um único elemento [(vencimento, 1000.0)] se o vencimento
        for após a data-base; lista vazia caso contrário.
    """
    if bond.vencimento > reference_date:
        return [(bond.vencimento, FACE_VALUE)]
    return []


def _generate_ntnf_cashflows(
    bond: BondRecord,
    reference_date: date,
) -> list[tuple[date, float]]:
    """
    Gera fluxos para NTN-F (cupons semestrais em 01/jan e 01/jul).

    Algoritmo:
      1. Parte do vencimento e vai subtraindo 6 meses por vez.
      2. Para cada data resultante que seja > reference_date, registra um cupom.
      3. No vencimento: pagamento = cupom + principal (1000).
      4. Ordena os fluxos cronologicamente.

    Parameters
    ----------
    bond : BondRecord
        Título NTN-F.
    reference_date : date
        Data-base do cálculo.

    Returns
    -------
    list[tuple[date, float]]
        Lista de (data_pagamento, valor) em ordem cronológica.
    """
    cashflows: list[tuple[date, float]] = []
    current_date = bond.vencimento

    # Primeiro pagamento (vencimento): cupom + principal
    if current_date > reference_date:
        cashflows.append((current_date, FACE_VALUE + NTNF_COUPON))

    # Percorre para trás, subtraindo 6 meses por vez
    current_date = _subtract_months(current_date, 6)
    while current_date > reference_date:
        cashflows.append((current_date, NTNF_COUPON))
        current_date = _subtract_months(current_date, 6)

    # Ordena cronologicamente (gerados de trás para frente)
    cashflows.sort(key=lambda cf: cf[0])
    return cashflows


def generate_all_cashflows(
    bonds: list[BondRecord],
    reference_date: date,
) -> dict[tuple[str, date], list[tuple[date, float]]]:
    """
    Gera fluxos de caixa para todos os títulos da lista.

    Parameters
    ----------
    bonds : list[BondRecord]
        Lista de títulos para os quais gerar fluxos.
    reference_date : date
        Data-base do cálculo.

    Returns
    -------
    dict[tuple[str, date], list[tuple[date, float]]]
        Dicionário com chave (tipo, vencimento) e valor sendo a lista de
        fluxos (data, valor) em ordem cronológica.
    """
    return {
        (bond.tipo, bond.vencimento): generate_cashflows(bond, reference_date)
        for bond in bonds
    }
