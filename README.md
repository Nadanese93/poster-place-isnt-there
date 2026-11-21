# VELMORA — Isles of the Amber Sea

A travel poster for a place that does not exist, written for the
[make.fun](https://make.fun) bounty **the-poster-for-a-place-that-i-2-20261121-0539**
($50 USDC prize).

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nadanese93/poster-place-isnt-there/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nadanese93/poster-place-isnt-there/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

VELMORA is an invented archipelago where islands float above the clouds
and waterfalls pour off their edges into golden mist. The poster is drawn
by a deterministic pure-stdlib renderer in the Art Deco travel-poster
style: a warm golden-hour sky, one low sun, three floating isles (one
with a lighthouse, one with a pavilion), and the place name set in large
geometric capitals that carry the poster's mood.

## Run

```sh
MAKEFUN_OUTPUT_DIR=/output python3 main.py
```

This writes the poster to `$MAKEFUN_OUTPUT_DIR/entry.png` (1024x1024 PNG,
about 55 KB). Python 3.13 standard library only, no network access,
deterministic: two runs produce byte-identical output.

## License

MIT — see [LICENSE](LICENSE).
