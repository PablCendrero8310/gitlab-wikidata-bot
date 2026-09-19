#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from random import sample

from httpx import AsyncClient

from gitlab_wikidata_bot.gitlab import (GitlabClient, analyse_release,
                                        get_releases)
from gitlab_wikidata_bot.main import logger
from gitlab_wikidata_bot.settings import Secrets, Settings, cache_root
from gitlab_wikidata_bot.sparql import cached_projects_query
from gitlab_wikidata_bot.wikidata_api import WikidataClient


def safe_sample[T](population: list[T], size: int) -> list[T]:
    try:
        return sample(population, size)
    except ValueError:
        return population


async def debug_version_handling(
    github: GitlabClient,
    wikidata: WikidataClient,
    settings: Settings,
    threshold: int = 50,
    size: int = 20,
    no_sampling: bool = False,
):
    logger.setLevel(40)
    projects = await cached_projects_query(False, wikidata, settings, None)
    if not no_sampling:
        projects = safe_sample(projects, threshold)
    for project in projects:
        project_info, _, _ = await github.fetch_json(project.repo.api_base())
        assert project_info is not None  # For the type checker
        repo_cache_root = (
            cache_root().joinpath(project.repo.org).joinpath(project.repo.project)
        )
        gitlab_releases = await get_releases(
            project.repo, repo_cache_root, github, False
        )
        if not no_sampling:
            gitlab_releases = safe_sample(gitlab_releases, size)
        for gitlab_release in gitlab_releases:
            release = analyse_release(gitlab_release, project_info["name"])
            print(
                "{:15} | {:10} | {:20} | {:25} | {}".format(
                    release.version if release else "---",
                    release.release_type if release else "---",
                    gitlab_release["tag_name"],
                    repr(project.label),
                    gitlab_release["name"],
                )
            )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", default=50, type=int)
    parser.add_argument("--maxsize", default=20, type=int)
    parser.add_argument("--no-sampling", action="store_true", default=False)
    args = parser.parse_args()

    secrets = Secrets.load()
    settings = Settings()
    async with AsyncClient(
        timeout=settings.http_timeout, headers={"User-Agent": settings.user_agent}
    ) as client:
        github = GitlabClient(secrets, client, settings)
        wikidata = WikidataClient(client, secrets, settings)
        await wikidata.connect(settings)
        await debug_version_handling(
            github, wikidata, settings, args.threshold, args.maxsize, args.no_sampling
        )


if __name__ == "__main__":
    asyncio.run(main())
