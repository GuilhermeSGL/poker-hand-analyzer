# poker-hand-analyzer (`pokerhud`)

> *Pure-Python hand history parser for PokerStars that computes HUD stats (VPIP, PFR, 3-bet, AF, WTSD, W$SD, bb/100), classifies player styles and flags coaching leaks. No dependencies, fully tested.*

Lê os arquivos de histórico de mãos da PokerStars e gera, para cada jogador, as estatísticas que um HUD mostra, a classificação de estilo e **alertas de coaching**. Útil para revisar a sessão de um jogador do time ou estudar os adversários.

```text
$ python -m pokerhud samples --min-hands 1

6 mãos analisadas

Jogador  Mãos  VPIP  PFR  3bet   AF  WTSD  W$SD  Resultado   bb/100  Estilo
-------  ----  ----  ---  ----  ---  ----  ----  ---------  -------  -----------------------
Carol       6   33%  17%    0%  2.0   50%    0%      -1.60   -266.7  passivo pré-flop
Dave        6   33%   0%    0%  2.0   50%  100%      +1.73   +288.3  passivo pré-flop
Hero        6   83%  50%   33%    ∞   25%  100%     +11.04  +1840.0  LAG (solto e agressivo)
...

Pontos de atenção:
  • Dave: VPIP 33% vs PFR 0%: pagando demais pré-flop; prefira abrir com raise ou foldar.
```

*(6 mãos é só para demonstrar; estilos e alertas só aparecem por padrão a partir de 50 mãos.)*

## O que ele calcula

| Estatística | Definição usada |
|---|---|
| **VPIP** | % de mãos em que colocou dinheiro voluntariamente no pré-flop (blind e check no BB não contam) |
| **PFR** | % de mãos com raise no pré-flop |
| **3-bet** | raises diante de exatamente um raise ÷ vezes em que teve essa oportunidade |
| **AF** | (bets + raises) ÷ calls no pós-flop |
| **WTSD** | % das vezes em que viu o flop e foi ao showdown |
| **W$SD** | % dos showdowns vencidos |
| **Resultado / bb/100** | ganho líquido (prêmios − fichas investidas, já descontando aposta devolvida) |

O cálculo de fichas trata `raises X to Y` (Y é o total da rua), antes, blinds, all-ins e **uncalled bets**. Um teste garante que, em toda mão, a soma dos resultados de todos os jogadores mais o rake dá zero.

## Uso

```bash
python -m pokerhud <arquivos ou pastas> [opções]

  --player NOME     filtra jogadores (pode repetir)
  --min-hands N     amostra mínima para estilo e alertas (padrão 50)
  --sort hands|net|vpip
  --json            saída em JSON (para integrar com planilhas ou outros sistemas)
  --html ARQUIVO    relatório HTML responsivo, tema claro/escuro
```

Ou instale como comando:

```bash
pip install .
pokerhud "C:\Users\voce\AppData\Local\PokerStars\HandHistory" --player MeuNick --html relatorio.html
```

Sem dependências externas: só a biblioteca padrão do Python 3.10+.

## Arquitetura

```
pokerhud/
├── parser.py   texto → Hand (ações por rua, showdown, prêmios, rake) com regex
├── stats.py    Hand → PlayerStats; classificação de estilo; regras de leaks
├── report.py   tabela de terminal, JSON e HTML
└── cli.py      argparse
tests/          14 testes (unittest) sobre mãos de exemplo com resultado conhecido
samples/        mãos fictícias no formato PokerStars
```

```bash
python -m unittest discover -s tests -t .
```

## Próximos passos

- Suporte a GGPoker e outros formatos de sala.
- Estatísticas por posição (BTN, CO, blinds) e c-bet / fold to c-bet.
- Exportar o resultado das sessões direto para o [Poker Team Manager](https://github.com/GuilhermeSGL/poker-team-manager).

---
Feito por [Guilherme](https://github.com/GuilhermeSGL). Licença MIT.
