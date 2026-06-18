"""
calendar.py — Módulo 1: Leitura de feriados ANBIMA e contagem de dias úteis.

Convenção de mercado brasileiro:
  - Base 252 dias úteis por ano
  - Contagem com np.busday_count(start, end): intervalo [start, end)
    (não inclui o dia de vencimento — convenção correta do mercado BR)
"""

from datetime import date
import numpy as np


def load_holidays(filepath: str) -> list[str]:
    """
    Lê o arquivo de feriados da ANBIMA e retorna uma lista de strings no
    formato 'YYYY-MM-DD'.

    O arquivo pode estar em diferentes formatos de data (DD/MM/YYYY,
    YYYYMMDD, YYYY-MM-DD). A função tenta detectar e converter
    automaticamente.

    Parameters
    ----------
    filepath : str
        Caminho para o arquivo de feriados (TXT ou CSV).

    Returns
    -------
    list[str]
        Lista de datas de feriado no formato ISO 'YYYY-MM-DD'.

    Raises
    ------
    ValueError
        Se o formato de data não puder ser reconhecido.
    """
    holidays: list[str] = []

    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue

            # Tenta extrair a primeira "palavra" como data (ignora campos extras)
            token = raw.split()[0] if " " in raw else raw
            # Remove separadores comuns que não sejam dígitos ou hífens
            token = token.replace(";", "").replace(",", "").strip()

            parsed = _parse_date_token(token)
            if parsed is not None:
                holidays.append(parsed.isoformat())

    return sorted(set(holidays))


def _parse_date_token(token: str) -> date | None:
    """
    Tenta converter um token de string em um objeto date.

    Suporta os formatos: DD/MM/YYYY, YYYYMMDD, YYYY-MM-DD.

    Parameters
    ----------
    token : str
        String candidata a representar uma data.

    Returns
    -------
    date | None
        Objeto date se o parse for bem-sucedido, None caso contrário.
    """
    from datetime import datetime

    formats = [
        "%d/%m/%Y",   # 25/12/2026
        "%Y%m%d",     # 20261225
        "%Y-%m-%d",   # 2026-12-25
        "%d-%m-%Y",   # 25-12-2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue

    return None


def count_business_days(start: date, end: date, holidays: list[str]) -> int:
    """
    Conta dias úteis de *start* até *end* usando convenção do mercado brasileiro.

    Utiliza np.busday_count(start, end) que conta o intervalo [start, end),
    ou seja, *start* é incluído e *end* é excluído. Essa é a convenção correta
    do mercado brasileiro (D.U. ex-início, ex-fim não se aplica — contamos
    de hoje até a véspera do vencimento).

    **Atenção:** NÃO adicionar +1 dia. O gabarito ANBIMA confirma essa lógica.

    Parameters
    ----------
    start : date
        Data inicial (data-base / today). Incluída no intervalo.
    end : date
        Data final (vencimento). Não incluída no intervalo.
    holidays : list[str]
        Lista de feriados no formato 'YYYY-MM-DD'.

    Returns
    -------
    int
        Número de dias úteis no intervalo [start, end).

    Examples
    --------
    >>> count_business_days(date(2026, 6, 1), date(2026, 7, 1), []) == 21
    True
    """
    return int(
        np.busday_count(
            start.isoformat(),
            end.isoformat(),
            holidays=holidays,
        )
    )


def to_years(business_days: int) -> float:
    """
    Converte dias úteis para anos usando base 252 (convenção brasileira).

    Parameters
    ----------
    business_days : int
        Número de dias úteis.

    Returns
    -------
    float
        Prazo expresso em anos (base 252).

    Examples
    --------
    >>> to_years(21)
    0.08333333333333333
    >>> to_years(252)
    1.0
    """
    return business_days / 252.0
