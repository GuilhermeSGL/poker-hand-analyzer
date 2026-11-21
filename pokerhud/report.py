"""Saídas: tabela no terminal, JSON e relatório HTML."""

from __future__ import annotations

import html
import json

from .stats import PlayerStats, leaks, player_type

COLUMNS = ("Jogador", "Mãos", "VPIP", "PFR", "3bet", "AF", "WTSD", "W$SD", "Resultado", "bb/100", "Estilo")


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _af(x: float | None) -> str:
    return "—" if x is None else ("∞" if x == float("inf") else f"{x:.1f}")


def _num(x: float | None, fmt: str = "{:+.2f}") -> str:
    return "—" if x is None else fmt.format(x)


def rows(stats: list[PlayerStats], min_hands: int) -> list[list[str]]:
    return [[s.name, str(s.hands), _pct(s.vpip_pct), _pct(s.pfr_pct), _pct(s.threebet_pct), _af(s.af),
             _pct(s.wtsd_pct), _pct(s.wsd_pct), _num(s.net), _num(s.bb_per_100, "{:+.1f}"),
             player_type(s, min_hands)] for s in stats]


def table(stats: list[PlayerStats], min_hands: int) -> str:
    data = [list(COLUMNS)] + rows(stats, min_hands)
    widths = [max(len(r[i]) for r in data) for i in range(len(COLUMNS))]
    left = {0, len(COLUMNS) - 1}
    fmt = lambda r: "  ".join(c.ljust(w) if i in left else c.rjust(w) for i, (c, w) in enumerate(zip(r, widths))).rstrip()
    out = [fmt(data[0]), "  ".join("-" * w for w in widths)] + [fmt(r) for r in data[1:]]
    tips = [(s.name, t) for s in stats for t in leaks(s, min_hands)]
    if tips:
        out += ["", "Pontos de atenção:"] + [f"  • {n}: {t}" for n, t in tips]
    return "\n".join(out)


def to_json(stats: list[PlayerStats], min_hands: int) -> str:
    return json.dumps([{
        "player": s.name, "hands": s.hands, "vpip": s.vpip_pct, "pfr": s.pfr_pct, "threebet": s.threebet_pct,
        "af": None if s.af in (None, float("inf")) else s.af, "wtsd": s.wtsd_pct, "wsd": s.wsd_pct,
        "net": s.net, "bb_per_100": s.bb_per_100, "type": player_type(s, min_hands), "leaks": leaks(s, min_hands),
    } for s in stats], ensure_ascii=False, indent=2)


def to_html(stats: list[PlayerStats], min_hands: int, total_hands: int) -> str:
    head = "".join(f"<th>{html.escape(c)}</th>" for c in COLUMNS)
    body = ""
    for s, r in zip(stats, rows(stats, min_hands)):
        cls = "pos" if s.net > 0 else "neg" if s.net < 0 else ""
        cells = "".join(f'<td class="{cls if i in (8, 9) else ""}">{html.escape(c)}</td>' for i, c in enumerate(r))
        tips = "".join(f"<li>{html.escape(t)}</li>" for t in leaks(s, min_hands))
        body += f"<tr>{cells}</tr>" + (f'<tr class="tips"><td colspan="{len(COLUMNS)}"><ul>{tips}</ul></td></tr>' if tips else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Relatório de mãos</title>
<style>
:root{{--bg:#0d1412;--card:#15201d;--line:#273833;--text:#e8efe9;--muted:#8ea39b;--pos:#4fd39c;--neg:#f0706a}}
@media (prefers-color-scheme: light){{:root{{--bg:#f3f5f2;--card:#fff;--line:#dde4dd;--text:#14201b;--muted:#5d6f67;--pos:#13875a;--neg:#c8362f}}}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif;padding:24px 16px}}
main{{max-width:1100px;margin:auto}} h1{{font-size:20px;margin:0 0 4px}} p{{color:var(--muted);margin:0 0 16px}}
.wrap{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}}
table{{border-collapse:collapse;width:100%}} th,td{{padding:8px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th:first-child,td:first-child,th:last-child,td:last-child{{text-align:left}} th{{color:var(--muted);font-weight:500;font-size:12px}}
.pos{{color:var(--pos)}} .neg{{color:var(--neg)}} tr.tips td{{text-align:left;white-space:normal;color:var(--muted);font-size:13px}}
tr.tips ul{{margin:0;padding-left:18px}}
</style></head><body><main><h1>Relatório de mãos</h1>
<p>{total_hands} mãos · {len(stats)} jogadores · estilos e alertas a partir de {min_hands} mãos</p>
<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></main></body></html>"""
