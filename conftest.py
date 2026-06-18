"""
conftest.py — Configuração do pytest para resolver o pacote src.bootstrap.

Adiciona o diretório raiz do projeto ao sys.path para que os testes possam
importar src.bootstrap.* sem necessidade de instalar o pacote.
"""

import sys
import os

# Garante que o diretório raiz do projeto está no path de importação
sys.path.insert(0, os.path.dirname(__file__))
