"""Estatísticas de HUD por jogador e diagnóstico de estilo/leaks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .parser import Hand

VOLUNTARY = ("call", "bet", "raise")


@dataclass
class PlayerStats:
    name: str
    hands: int = 0
    vpip: int = 0
    pfr: int = 0
    threebet: int = 0
    threebet_opp: int = 0
    saw_flop: int = 0
    wtsd: int = 0
    won_sd: int = 0
    aggressive: int = 0  # bets + raises pós-flop
    calls: int = 0  # calls pós-flop
    net: float = 0.0
    net_bb: float = 0.0

    # ---- percentuais (None quando não há amostra)
    @staticmethod
    def _rate(num: int, den: int) -> float | None:
        return num / den if den else None

    @property
    def vpip_pct(self): return self._rate(self.vpip, self.hands)
    @property
    def pfr_pct(self): return self._rate(self.pfr, self.hands)
    @property
    def threebet_pct(self): return self._rate(self.threebet, self.threebet_opp)
    @property
    def wtsd_pct(self): return self._rate(self.wtsd, self.saw_flop)
    @property
    def wsd_pct(self): return self._rate(self.won_sd, self.wtsd)

    @property
    def af(self) -> float | None:
        """Fator de agressão pós-flop: (bets + raises) / calls."""
        if self.calls:
            return self.aggressive / self.calls
        return float("inf") if self.aggressive else None

    @property
    def bb_per_100(self) -> float | None:
        return self.net_bb / self.hands * 100 if self.hands else None


def compute(hands: list[Hand]) -> dict[str, PlayerStats]:
    players: dict[str, PlayerStats] = defaultdict(lambda: PlayerStats(""))
    for hand in hands:
        _add_hand(hand, players)
    for name, st in players.items():
        st.name = name
    return dict(players)


def _add_hand(hand: Hand, players: dict[str, PlayerStats]) -> None:
    folded_pre: set[str] = set()
    raises = 0  # raises já feitos no preflop (blinds não contam)
    seen_3b_spot: set[str] = set()
    vpip: set[str] = set()
    pfr: set[str] = set()

    for a in hand.street_actions("preflop"):
        if a.kind in ("post", "ante"):
            continue
        st = players[a.player]
        # spot de 3-bet: primeira vez que o jogador age diante de exatamente um raise
        if raises == 1 and a.player not in seen_3b_spot:
            seen_3b_spot.add(a.player)
            st.threebet_opp += 1
            if a.kind == "raise":
                st.threebet += 1
        if a.kind in VOLUNTARY:
            vpip.add(a.player)
        if a.kind == "raise":
            pfr.add(a.player)
            raises += 1
        if a.kind == "fold":
            folded_pre.add(a.player)

    has_flop = "flop" in hand.board_streets
    for name in hand.seats:
        st = players[name]
        st.hands += 1
        st.vpip += name in vpip
        st.pfr += name in pfr
        if has_flop and name not in folded_pre:
            st.saw_flop += 1
            if name in hand.showdown:
                st.wtsd += 1
                st.won_sd += hand.collected.get(name, 0) > 0
        net = hand.net(name)
        st.net = round(st.net + net, 2)
        st.net_bb += net / hand.bb

    for a in hand.actions:
        if a.street == "preflop":
            continue
        if a.kind in ("bet", "raise"):
            players[a.player].aggressive += 1
        elif a.kind == "call":
            players[a.player].calls += 1


def player_type(s: PlayerStats, min_hands: int = 50) -> str:
    """Classificação de estilo pelos números clássicos de VPIP/PFR."""
    if s.hands < min_hands:
        return "amostra pequena"
    v, p = s.vpip_pct * 100, s.pfr_pct * 100
    if v >= 40 and p < 15:
        return "fish / calling station"
    if v >= 30 and p >= 22:
        return "LAG (solto e agressivo)"
    if v < 15:
        return "nit (muito fechado)"
    if 15 <= v <= 28 and p >= v * 0.7:
        return "TAG (regular sólido)"
    if v - p > 10:
        return "passivo pré-flop"
    return "regular"


def leaks(s: PlayerStats, min_hands: int = 50) -> list[str]:
    """Alertas de coaching a partir das estatísticas (faixas de referência para 6-max)."""
    if s.hands < min_hands:
        return []
    out = []
    v, p = s.vpip_pct * 100, s.pfr_pct * 100
    if v - p > 10:
        out.append(f"VPIP {v:.0f}% vs PFR {p:.0f}%: pagando demais pré-flop; prefira abrir com raise ou foldar.")
    if s.threebet_pct is not None and s.threebet_opp >= 20 and s.threebet_pct < 0.04:
        out.append(f"3-bet de {s.threebet_pct:.0%}: baixo; fica explorável por quem abre muitas mãos.")
    if s.wtsd_pct is not None and s.saw_flop >= 30:
        if s.wtsd_pct > 0.33:
            out.append(f"WTSD de {s.wtsd_pct:.0%}: vai demais ao showdown; revise calls de river.")
        elif s.wtsd_pct < 0.20:
            out.append(f"WTSD de {s.wtsd_pct:.0%}: desiste cedo demais; pode estar sofrendo blefes.")
    af = s.af
    if af is not None and af != float("inf") and s.calls >= 20 and af < 1.5:
        out.append(f"AF de {af:.1f}: jogo pós-flop passivo; aposte mais por valor e com draws.")
    return out
