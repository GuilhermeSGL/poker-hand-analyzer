"""Parser de hand histories no formato PokerStars (Hold'em, cash e torneio)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

STREETS = ("preflop", "flop", "turn", "river")

RE_HEADER = re.compile(r"^PokerStars (?:Hand|Game) #(\d+):")
RE_BLINDS = re.compile(r"\(\$?([\d.,]+)/\$?([\d.,]+)")
RE_DATE = re.compile(r" - (\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}:\d{2})")
RE_TABLE = re.compile(r"^Table '(.+?)'.*Seat #(\d+) is the button")
RE_SEAT = re.compile(r"^Seat (\d+): (.+?) \(\$?([\d.,]+) in chips")
RE_DEALT = re.compile(r"^Dealt to (.+?) \[(.+?)\]")
RE_ACTION = re.compile(r"^(.+?): (folds|checks|calls|bets|raises|posts)\b(.*)$")
RE_RAISE_TO = re.compile(r"to \$?([\d.,]+)")
RE_AMOUNT = re.compile(r"\$?([\d.,]+)")
RE_UNCALLED = re.compile(r"^Uncalled bet \(\$?([\d.,]+)\) returned to (.+)$")
RE_COLLECTED = re.compile(r"^(.+?) collected \$?([\d.,]+) from")
RE_SHOWDOWN = re.compile(r"^(.+?): (shows|mucks)")
RE_RAKE = re.compile(r"^Total pot \$?([\d.,]+).*?Rake \$?([\d.,]+)")
RE_STREET = re.compile(r"^\*\*\* (HOLE CARDS|FLOP|TURN|RIVER|SHOW ?DOWN|SUMMARY) \*\*\*")


def money(text: str) -> float:
    return float(text.replace(",", ""))


@dataclass
class Action:
    player: str
    street: str
    kind: str  # post, ante, fold, check, call, bet, raise
    amount: float = 0.0  # fichas colocadas nesta ação (para raise: o valor "to")


@dataclass
class Hand:
    id: str
    sb: float
    bb: float
    date: str = ""
    table: str = ""
    button: int = 0
    seats: dict[str, float] = field(default_factory=dict)
    hero: str | None = None
    hero_cards: str | None = None
    actions: list[Action] = field(default_factory=list)
    board_streets: set[str] = field(default_factory=set)
    showdown: set[str] = field(default_factory=set)
    collected: dict[str, float] = field(default_factory=dict)
    returned: dict[str, float] = field(default_factory=dict)
    total_pot: float = 0.0
    rake: float = 0.0

    def street_actions(self, street: str) -> list[Action]:
        return [a for a in self.actions if a.street == street]

    def invested(self, player: str) -> float:
        """Total de fichas que o jogador colocou no pote (descontando a aposta devolvida)."""
        total = 0.0
        for street in STREETS:
            committed = 0.0
            for a in self.street_actions(street):
                if a.player != player:
                    continue
                if a.kind == "ante":
                    total += a.amount
                elif a.kind == "raise":
                    committed = a.amount  # "raises X to Y": Y é o total da rua
                elif a.kind in ("post", "call", "bet"):
                    committed += a.amount
            total += committed
        return round(total - self.returned.get(player, 0.0), 2)

    def net(self, player: str) -> float:
        return round(self.collected.get(player, 0.0) - self.invested(player), 2)


def parse_hand(text: str) -> Hand:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    header = lines[0].lstrip("﻿")
    m = RE_HEADER.match(header)
    if not m:
        raise ValueError(f"Cabeçalho de mão não reconhecido: {header[:60]!r}")
    blinds = RE_BLINDS.search(header)
    if not blinds:
        raise ValueError(f"Blinds não encontrados na mão #{m.group(1)}")
    date = RE_DATE.search(header)
    hand = Hand(id=m.group(1), sb=money(blinds.group(1)), bb=money(blinds.group(2)),
                date=date.group(1) if date else "")

    section = "setup"
    for line in lines[1:]:
        if st := RE_STREET.match(line):
            name = st.group(1).replace(" ", "")
            section = {"HOLECARDS": "preflop", "FLOP": "flop", "TURN": "turn", "RIVER": "river",
                       "SHOWDOWN": "showdown", "SUMMARY": "summary"}[name]
            if section in ("flop", "turn", "river"):
                hand.board_streets.add(section)
            continue

        if section == "summary":
            if r := RE_RAKE.match(line):
                hand.total_pot, hand.rake = money(r.group(1)), money(r.group(2))
            continue

        if section == "setup":
            if t := RE_TABLE.match(line):
                hand.table, hand.button = t.group(1), int(t.group(2))
                continue
            if s := RE_SEAT.match(line):
                hand.seats[s.group(2)] = money(s.group(3))
                continue

        if d := RE_DEALT.match(line):
            hand.hero, hand.hero_cards = d.group(1), d.group(2)
            continue
        if u := RE_UNCALLED.match(line):
            hand.returned[u.group(2)] = hand.returned.get(u.group(2), 0.0) + money(u.group(1))
            continue
        if c := RE_COLLECTED.match(line):
            hand.collected[c.group(1)] = round(hand.collected.get(c.group(1), 0.0) + money(c.group(2)), 2)
            continue
        if section == "showdown" and (sd := RE_SHOWDOWN.match(line)):
            hand.showdown.add(sd.group(1))
            continue
        if a := RE_ACTION.match(line):
            player, verb, rest = a.groups()
            if player not in hand.seats:
                continue  # linha de chat ou algo que não é ação de jogador sentado
            street = "preflop" if section == "setup" else section
            hand.actions.append(_action(player, street, verb, rest))
    return hand


def _action(player: str, street: str, verb: str, rest: str) -> Action:
    if verb == "raises":
        return Action(player, street, "raise", money(RE_RAISE_TO.search(rest).group(1)))
    if verb == "posts":
        amount = money(RE_AMOUNT.search(rest.split()[-1]).group(1))
        return Action(player, street, "ante" if "ante" in rest else "post", amount)
    if verb in ("calls", "bets"):
        return Action(player, street, verb[:-1], money(RE_AMOUNT.search(rest).group(1)))
    return Action(player, street, verb[:-1] if verb == "folds" else "check")


def split_hands(text: str) -> Iterator[str]:
    """Divide um arquivo em blocos, um por mão."""
    block: list[str] = []
    for line in text.splitlines():
        if RE_HEADER.match(line.lstrip("﻿")) and block:
            yield "\n".join(block)
            block = []
        if block or RE_HEADER.match(line.lstrip("﻿")):
            block.append(line)
    if block:
        yield "\n".join(block)


def load_hands(paths: Iterable[str | Path]) -> tuple[list[Hand], list[str]]:
    """Lê arquivos ou pastas (.txt). Retorna as mãos e a lista de erros de parse."""
    hands: list[Hand] = []
    errors: list[str] = []
    files: list[Path] = []
    for p in map(Path, paths):
        files.extend(sorted(p.rglob("*.txt")) if p.is_dir() else [p])
    for f in files:
        for block in split_hands(f.read_text(encoding="utf-8-sig", errors="replace")):
            try:
                hands.append(parse_hand(block))
            except (ValueError, AttributeError) as exc:
                errors.append(f"{f.name}: {exc}")
    return hands, errors
