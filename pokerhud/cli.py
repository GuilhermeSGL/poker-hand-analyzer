"""Linha de comando: python -m pokerhud <arquivos ou pastas> [opções]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report
from .parser import load_hands
from .stats import compute


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pokerhud", description="Estatísticas de HUD a partir de hand histories da PokerStars.")
    ap.add_argument("paths", nargs="+", help="arquivos .txt ou pastas com hand histories")
    ap.add_argument("--player", action="append", help="mostrar só este jogador (pode repetir)")
    ap.add_argument("--min-hands", type=int, default=50, help="mínimo de mãos para estilo e alertas (padrão 50)")
    ap.add_argument("--sort", choices=("hands", "net", "vpip"), default="hands")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    ap.add_argument("--html", metavar="ARQUIVO", help="gera também um relatório HTML")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    hands, errors = load_hands(args.paths)
    if not hands:
        print("Nenhuma mão encontrada.", file=sys.stderr)
        return 1

    stats = list(compute(hands).values())
    if args.player:
        stats = [s for s in stats if s.name in args.player]
    key = {"hands": lambda s: s.hands, "net": lambda s: s.net, "vpip": lambda s: s.vpip_pct or 0}[args.sort]
    stats.sort(key=key, reverse=True)

    if args.json:
        print(report.to_json(stats, args.min_hands))
    else:
        print(f"{len(hands)} mãos analisadas\n")
        print(report.table(stats, args.min_hands))
    if args.html:
        Path(args.html).write_text(report.to_html(stats, args.min_hands, len(hands)), encoding="utf-8")
        print(f"\nRelatório salvo em {args.html}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} mão(s) ignoradas por erro de leitura.", file=sys.stderr)
    return 0
