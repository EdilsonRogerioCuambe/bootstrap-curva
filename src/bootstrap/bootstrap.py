"""
bootstrap.py — Módulo 6: Orquestrador do bootstrapping da curva zero-cupom.

Chama todos os módulos na ordem correta e retorna a curva zero-cupom completa
em formato de dicionário Python pronto para serialização (JSON, etc.).

Fluxo de execução:
  1. parse_anbima_txt       → lista de BondRecord
  2. load_holidays          → lista de feriados
  3. generate_all_cashflows → fluxos por título
  4. build_system           → matriz C e vetor P
  5. solve_discount_factors → fatores de desconto d
  6. validate_repricing     → erro de re-precificação (R5)
  7. discount_to_spot       → taxas spot anuais
  8. Monta e retorna o dict de saída

Uso como script:
  pipenv run python -m src.bootstrap.bootstrap \\
      --prices  data/precos.txt \\
      --holidays data/feriados.txt \\
      --date    2026-06-01
"""

import argparse
import json
import sys
from datetime import date

from src.bootstrap.calendar import load_holidays
from src.bootstrap.cashflows import generate_all_cashflows
from src.bootstrap.matrix import build_system
from src.bootstrap.parser import parse_anbima_txt
from src.bootstrap.solver import (
    discount_to_spot,
    solve_discount_factors,
    validate_repricing,
)


def build_zero_curve(
    prices_filepath: str,
    holidays_filepath: str,
    reference_date: date,
) -> dict:
    """
    Orquestra o bootstrapping completo da curva zero-cupom brasileira.

    Parameters
    ----------
    prices_filepath : str
        Caminho para o arquivo TXT de preços da ANBIMA
        (formato separado por '@').
    holidays_filepath : str
        Caminho para o arquivo de feriados da ANBIMA.
    reference_date : date
        Data-base do cálculo (ex: date(2026, 6, 1)).

    Returns
    -------
    dict
        Dicionário com a curva zero-cupom:
        {
            "data_base": "YYYY-MM-DD",
            "erro_reprecificacao": <float>,
            "curva": [
                {
                    "data": "YYYY-MM-DD",
                    "du": <int>,
                    "prazo_anos": <float>,
                    "fator_desconto": <float>,
                    "taxa_spot": <float>
                },
                ...
            ]
        }

    Raises
    ------
    AssertionError
        Se o erro de re-precificação superar 1e-4 (falha no requisito R5).
    FileNotFoundError
        Se algum dos arquivos de entrada não existir.
    ValueError
        Se os arquivos de entrada estiverem em formato inesperado.

    Examples
    --------
    >>> from datetime import date
    >>> result = build_zero_curve(
    ...     "data/precos_20260601.txt",
    ...     "data/feriados.txt",
    ...     date(2026, 6, 1)
    ... )
    >>> result["data_base"]
    '2026-06-01'
    """
    # Passo 1: Lê títulos e feriados
    bonds = parse_anbima_txt(prices_filepath)
    holidays = load_holidays(holidays_filepath)

    # Passo 2: Gera fluxos de caixa para todos os títulos
    cashflows = generate_all_cashflows(bonds, reference_date)

    # Passo 3: Monta o sistema linear C * d = P
    C, P, payment_dates, dus, years = build_system(
        bonds, cashflows, reference_date, holidays
    )

    # Passo 4: Resolve o sistema para obter fatores de desconto
    d = solve_discount_factors(C, P)

    # Passo 5: Valida re-precificação (Requisito R5)
    repricing_error = validate_repricing(C, d, P)

    # Passo 6: Converte fatores de desconto para taxas spot anuais
    spot_rates = discount_to_spot(d, years)

    # Monta o resultado final
    curva = [
        {
            "data": payment_dates[j].isoformat(),
            "du": dus[j],
            "prazo_anos": round(years[j], 6),
            "fator_desconto": round(float(d[j]), 6),
            "taxa_spot": round(float(spot_rates[j]), 6),
        }
        for j in range(len(payment_dates))
    ]

    return {
        "data_base": reference_date.isoformat(),
        "erro_reprecificacao": round(repricing_error, 10),
        "curva": curva,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Analisa argumentos de linha de comando para uso como script.

    Parameters
    ----------
    argv : list[str] | None
        Lista de argumentos. Se None, usa sys.argv[1:].

    Returns
    -------
    argparse.Namespace
        Namespace com os campos: prices, holidays, date.
    """
    parser = argparse.ArgumentParser(
        description="Bootstrapping da curva zero-cupom ANBIMA"
    )
    parser.add_argument(
        "--prices",
        required=True,
        help="Caminho para o TXT de preços da ANBIMA (separado por '@')",
    )
    parser.add_argument(
        "--holidays",
        required=True,
        help="Caminho para o arquivo de feriados da ANBIMA",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Data-base no formato YYYY-MM-DD (ex: 2026-06-01)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """
    Ponto de entrada para uso como script via linha de comando.

    Exemplo de uso:
        pipenv run python -m src.bootstrap.bootstrap \\
            --prices  data/precos.txt \\
            --holidays data/feriados.txt \\
            --date    2026-06-01

    Parameters
    ----------
    argv : list[str] | None
        Argumentos de linha de comando. Se None, usa sys.argv[1:].
    """
    args = _parse_args(argv)
    reference_date = date.fromisoformat(args.date)

    result = build_zero_curve(
        prices_filepath=args.prices,
        holidays_filepath=args.holidays,
        reference_date=reference_date,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
