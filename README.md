# nsec_challenge_scraper
Tools for automatically posting new challenges to discord/slack/whatever as they appear

## scrape_discourse.py
This will output a json blob of the new posts since the last time the script was run (state is stored in `sync.db`, a local sqlite db). Doesn't post anywhere on its own.

## post_discord.py
This requires a discord bot account in a dedicated team discord server to work. It creates one channel per challenge topic discovered, and places them in the configured landing zone category. The bot needs the `messages` privileged intent.

