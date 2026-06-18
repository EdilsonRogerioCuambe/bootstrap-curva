"""
parser.py — Módulo 2: Leitura e parse do arquivo TXT de preços da ANBIMA.

Formato do TXT ANBIMA: separado por '@', com cabeçalho descartável.
Filtra apenas LTN e NTN-F (títulos pré-fixados).

Formato de cada linha de dado:
  TIPO@DATA_REF@COD_SELIC@EMISSAO@VENCIMENTO@TX_COMPRA@TX_VENDA@TX_INDICATIVA@PU@...

Exemplo real (data-base 2026-06-01):
  LTN@20260601@100000@20230106@20260701@14,3883@14,3711@14,3798@988,866252@...
  NTN-F@20260601@950199@20160115@20270101@14,071@14,0332@14,0521@1019,143414@...
"""

from dataclasses import dataclass
from datetime import date, datetime


# Tipos de títulos pré-fixados suportados
SUPPORTED_BOND_TYPES = {"LTN", "NTN-F"}


@dataclass
class BondRecord:
    """
    Representa um título pré-fixado lido do arquivo TXT da ANBIMA.

    Attributes
    ----------
    tipo : str
        Tipo do título: 'LTN' ou 'NTN-F'.
    vencimento : date
        Data de vencimento do título.
    pu : float
        Preço Unitário (PU) de mercado publicado pela ANBIMA.
    tx_indicativa : float
        Taxa indicativa ANBIMA em decimal (ex: 0.143798 para 14.3798% a.a.).
        Usada para validação da curva calculada.
    """

    tipo: str
    vencimento: date
    pu: float
    tx_indicativa: float


def _parse_float_br(value: str) -> float:
    """
    Converte string de número no formato brasileiro (vírgula decimal) para float.

    Parameters
    ----------
    value : str
        Número como string, podendo usar vírgula como separador decimal.

    Returns
    -------
    float
        Valor numérico correspondente.

    Examples
    --------
    >>> _parse_float_br('988,866252')
    988.866252
    >>> _parse_float_br('14.3798')
    14.3798
    """
    return float(value.strip().replace(",", "."))


def _parse_date_anbima(value: str) -> date:
    """
    Converte data no formato YYYYMMDD (padrão ANBIMA) para objeto date.

    Parameters
    ----------
    value : str
        Data no formato 'YYYYMMDD'.

    Returns
    -------
    date
        Objeto date correspondente.

    Raises
    ------
    ValueError
        Se o formato não for reconhecido.
    """
    return datetime.strptime(value.strip(), "%Y%m%d").date()


def parse_anbima_txt(filepath: str) -> list[BondRecord]:
    """
    Lê o arquivo TXT de preços da ANBIMA e retorna lista de BondRecord.

    O arquivo é separado por '@'. Linhas que não começam com um tipo
    suportado (LTN, NTN-F) são ignoradas (cabeçalho, rodapé, etc.).

    Mapeamento de colunas (índice base 0):
      0 — tipo do título
      1 — data de referência (YYYYMMDD)
      2 — código SELIC
      3 — data de emissão (YYYYMMDD)
      4 — data de vencimento (YYYYMMDD)
      5 — taxa de compra (% a.a.)
      6 — taxa de venda (% a.a.)
      7 — taxa indicativa (% a.a.)
      8 — PU (preço unitário)

    Parameters
    ----------
    filepath : str
        Caminho para o arquivo TXT de preços da ANBIMA.

    Returns
    -------
    list[BondRecord]
        Lista de títulos pré-fixados (LTN e NTN-F) ordenados por vencimento
        crescente (necessário para garantir triangularidade da matriz C).

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    ValueError
        Se uma linha de dado tiver formato inesperado.
    """
    records: list[BondRecord] = []

    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue

            parts = raw.split("@")
            if len(parts) < 9:
                # Linha de cabeçalho ou rodapé — ignorar
                continue

            tipo = parts[0].strip()
            if tipo not in SUPPORTED_BOND_TYPES:
                continue

            try:
                vencimento = _parse_date_anbima(parts[4])
                tx_indicativa = _parse_float_br(parts[7]) / 100.0  # % → decimal
                pu = _parse_float_br(parts[8])
            except (ValueError, IndexError) as exc:
                raise ValueError(
                    f"Erro ao processar linha {line_num}: '{raw}'"
                ) from exc

            records.append(
                BondRecord(
                    tipo=tipo,
                    vencimento=vencimento,
                    pu=pu,
                    tx_indicativa=tx_indicativa,
                )
            )

    # Ordena por vencimento crescente para garantir triangularidade da matriz C
    records.sort(key=lambda r: r.vencimento)
    return records
