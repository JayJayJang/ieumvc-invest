# CLAUDE.md

## Language
- Communicate with the user in **English** by default (replies, questions, summaries, commit messages), even when the user writes in Korean. Switch only if the user asks for another language.
- Site content stays bilingual: every brief in `content/<date>.json` carries both `en` and `kr` fields.

## Briefs
- Follow the "Price rules (no estimates)" section in `README.md`: KRX regular-session closes for Korean prices, US Treasury par yields for rates, no derived or intraday figures presented as closes.
- **Watchlist universe** — from the 16 Nov 2026 brief on, the watchlist covers every name in the "Watchlist universe" table in `README.md`, not only the names in the newest content file. Each stock row keeps the existing format (archetype, driver, last price with KRX-close tag and foreign ownership, level, status); price and ownership come from the Daum Finance endpoints listed there. Keep the KOSDAQ index row last.
- **Watchlist priority** — before writing the watchlist, run `python scripts/watch.py` and order the rows by the "Watchlist priority" rules in `README.md`: every row gets `priority` (HIGH/MEDIUM/LOW) and a bilingual `trigger` line saying what in the previous sessions set the rank. Raise a rank for a disclosure, ruling or major story the script cannot see; never lower one it set.
