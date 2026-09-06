#!/usr/bin/env python3
"""
CogniMove — Ferramenta CLI de Manutenção e Limpeza de Evidências

Remove screenshots, mini-clips e relatórios antigos armazenados em backend/outputs/
para evitar o esgotamento do espaço em disco em execuções de longa duração.

EXEMPLOS DE USO:
  # 1. Simular limpeza de evidências com mais de 30 dias (sem apagar nada):
  python backend/detection/limpar_evidencias_cli.py --dry-run

  # 2. Remover evidências com mais de 15 dias:
  python backend/detection/limpar_evidencias_cli.py --dias 15

  # 3. Limpar evidências e também o diretório de relatórios antigos:
  python backend/detection/limpar_evidencias_cli.py --dias 30 --incluir-relatorios

  # 4. Limpar um diretório customizado:
  python backend/detection/limpar_evidencias_cli.py --diretorio backend/outputs/evidencias/screenshots --dias 7
"""
import sys
import argparse
from pathlib import Path

# Ajustar sys.path para importar o módulo de limpeza
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.limpeza import limpar_evidencias_antigas

DEFAULT_EVIDENCIAS_DIR = PROJECT_ROOT / "backend" / "outputs" / "evidencias"
DEFAULT_RELATORIOS_DIR = PROJECT_ROOT / "backend" / "outputs" / "relatorios"


def main():
    parser = argparse.ArgumentParser(
        description="Ferramenta de manutenção para remoção de evidências e relatórios antigos do CogniMove."
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=30,
        help="Número de dias de retenção. Arquivos modificados a mais tempo serão removidos. Padrão: 30"
    )
    parser.add_argument(
        "--diretorio", "-d",
        type=str,
        default=str(DEFAULT_EVIDENCIAS_DIR),
        help=f"Diretório a ser limpo. Padrão: {DEFAULT_EVIDENCIAS_DIR}"
    )
    parser.add_argument(
        "--incluir-relatorios",
        action="store_true",
        help=f"Também aplica a limpeza ao diretório de relatórios ({DEFAULT_RELATORIOS_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo de simulação: lista os arquivos que seriam removidos sem deletá-los."
    )

    args = parser.parse_args()

    diretorio_alvo = Path(args.diretorio)
    if not diretorio_alvo.is_absolute():
        diretorio_alvo = (PROJECT_ROOT / diretorio_alvo).resolve()

    modo_str = "[MODO SIMULAÇÃO / DRY-RUN]" if args.dry_run else "[MODO REMOÇÃO REAL]"
    print("\n" + "=" * 75)
    print(f"  [CogniMove] Manutenção de Disco — Limpeza de Evidências {modo_str}")
    print(f"  Diretório: {diretorio_alvo}")
    print(f"  Retenção: {args.dias} dias")
    print("=" * 75)

    removidos_evidencias = limpar_evidencias_antigas(
        diretorio=diretorio_alvo,
        dias_retencao=args.dias,
        dry_run=args.dry_run
    )

    removidos_relatorios = 0
    if args.incluir_relatorios:
        print(f"\n[RELATÓRIOS] Limpando diretório de relatórios: {DEFAULT_RELATORIOS_DIR}")
        removidos_relatorios = limpar_evidencias_antigas(
            diretorio=DEFAULT_RELATORIOS_DIR,
            dias_retencao=args.dias,
            dry_run=args.dry_run
        )

    total_removidos = removidos_evidencias + removidos_relatorios

    print("\n" + "-" * 75)
    if args.dry_run:
        print(f"📊 RESUMO: {total_removidos} arquivo(s) seriam removidos.")
    else:
        print(f"🧹 RESUMO: {total_removidos} arquivo(s) foram removidos com sucesso.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
