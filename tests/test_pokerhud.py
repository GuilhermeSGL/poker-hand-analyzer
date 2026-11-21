import json
import unittest
from pathlib import Path

from pokerhud import compute, leaks, load_hands, parse_hand, player_type
from pokerhud.cli import main
from pokerhud.stats import PlayerStats

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "pokerstars_6max.txt"


class ParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hands, cls.errors = load_hands([SAMPLE])

    def test_le_todas_as_maos(self):
        self.assertEqual(len(self.hands), 6)
        self.assertEqual(self.errors, [])

    def test_cabecalho_e_mesa(self):
        h = self.hands[0]
        self.assertEqual((h.id, h.sb, h.bb), ("250000000001", 0.05, 0.10))
        self.assertEqual((h.table, h.button, len(h.seats)), ("Alpha", 1, 6))
        self.assertEqual((h.hero, h.hero_cards), ("Hero", "Ah Kd"))

    def test_fichas_se_conservam_em_toda_mao(self):
        # tudo o que os jogadores ganharam/perderam + o rake tem que somar zero
        for h in self.hands:
            total = sum(h.net(p) for p in h.seats) + h.rake
            self.assertAlmostEqual(total, 0, places=2, msg=f"mão {h.id}")

    def test_aposta_devolvida_nao_conta_como_investida(self):
        h = self.hands[0]
        self.assertAlmostEqual(h.invested("Hero"), 0.70)
        self.assertAlmostEqual(h.net("Hero"), 0.73)

    def test_raise_to_substitui_o_valor_da_rua(self):
        h = self.hands[2]  # Hero paga 0.10, paga +0.30, depois raise to 2.00 no flop
        self.assertAlmostEqual(h.invested("Hero"), 10.00)
        self.assertEqual(h.showdown, {"Hero", "Bob"})

    def test_formato_de_torneio_e_ante(self):
        text = """PokerStars Hand #1: Tournament #9, $10+$1 USD Hold'em No Limit - Level II (15/30) - 2026/11/01 10:00:00 ET
Table '9 1' 9-max Seat #1 is the button
Seat 1: A (1500 in chips)
Seat 2: B (1500 in chips)
A: posts the ante 5
B: posts the ante 5
A: posts small blind 15
B: posts big blind 30
*** HOLE CARDS ***
A: raises 60 to 90
B: folds
Uncalled bet (60) returned to A
A collected 70 from pot
*** SUMMARY ***
Total pot 70 | Rake 0"""
        h = parse_hand(text)
        self.assertEqual((h.sb, h.bb), (15, 30))
        self.assertEqual(h.net("A"), 35)
        self.assertEqual(h.net("B"), -35)

    def test_cabecalho_invalido(self):
        with self.assertRaises(ValueError):
            parse_hand("isto não é uma mão")


class StatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = compute(load_hands([SAMPLE])[0])

    def test_hero(self):
        s = self.stats["Hero"]
        self.assertEqual((s.hands, s.vpip, s.pfr), (6, 5, 3))
        self.assertEqual((s.threebet, s.threebet_opp), (1, 3))
        self.assertEqual((s.saw_flop, s.wtsd, s.won_sd), (4, 1, 1))
        self.assertEqual(s.af, float("inf"))  # só apostou e aumentou pós-flop
        self.assertAlmostEqual(s.net, 11.04)
        self.assertAlmostEqual(s.bb_per_100, 1840)

    def test_alice_completa_o_sb_e_da_3bet(self):
        s = self.stats["Alice"]
        self.assertEqual((s.vpip, s.pfr, s.threebet, s.threebet_opp), (3, 1, 1, 2))
        self.assertAlmostEqual(s.net, -0.50)

    def test_bb_que_da_check_nao_entra_no_vpip(self):
        self.assertEqual(self.stats["Bob"].vpip, 1)  # só a mão 3

    def test_fator_de_agressao(self):
        self.assertAlmostEqual(self.stats["Carol"].af, 2.0)

    def test_estilo_e_leaks_respeitam_amostra_minima(self):
        s = self.stats["Hero"]
        self.assertEqual(player_type(s, min_hands=50), "amostra pequena")
        self.assertEqual(leaks(s, min_hands=50), [])

    def test_classificacao(self):
        fish = PlayerStats("x", hands=200, vpip=100, pfr=10)
        tag = PlayerStats("y", hands=200, vpip=44, pfr=38)
        self.assertEqual(player_type(fish), "fish / calling station")
        self.assertEqual(player_type(tag), "TAG (regular sólido)")
        self.assertTrue(any("pagando demais" in t for t in leaks(fish)))


class CliTest(unittest.TestCase):
    def test_json(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([str(SAMPLE), "--json", "--player", "Hero"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data[0]["player"], "Hero")
        self.assertEqual(data[0]["hands"], 6)


if __name__ == "__main__":
    unittest.main()
