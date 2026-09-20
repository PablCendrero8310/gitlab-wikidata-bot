#!/usr/bin/env python3

from __future__ import annotations

import asyncio

from gitlab_wikidata_bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
