# CLAUDE.md

## Language
- Communicate with the user in **English** by default (replies, questions, summaries, commit messages), even when the user writes in Korean. Switch only if the user asks for another language.
- Site content stays bilingual: every brief in `content/<date>.json` carries both `en` and `kr` fields.

## Briefs
- Follow the "Price rules (no estimates)" section in `README.md`: KRX regular-session closes for Korean prices, US Treasury par yields for rates, no derived or intraday figures presented as closes.
