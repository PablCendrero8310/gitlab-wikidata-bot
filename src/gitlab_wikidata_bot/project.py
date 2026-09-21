from __future__ import annotations

from dataclasses import dataclass
from shlex import quote
from typing import Self

from yarl import URL

WIKIDATA_PREFIX = "http://www.wikidata.org/entity/"


class InvalidProject(ValueError):
    """A Wikidata project contains invalid data and should be skipped."""


@dataclass(frozen=True)
class WikidataProject:
    # Ex) Q42
    q_value: str
    # The wikidata label, english preferred.
    label: str
    repo: GitLabRepo

    @property
    def q_value_url(self) -> str:
        """The full URL. Ex) `http://www.wikidata.org/entity/Q42`."""
        return WIKIDATA_PREFIX + self.q_value

    @classmethod
    def from_sparql(cls, project: dict[str, str]) -> Self:
        url = project["project"]
        if not url.startswith(WIKIDATA_PREFIX):
            raise InvalidProject(f"Invalid wikidata entity URL: {url}")
        q_value = url.removeprefix(WIKIDATA_PREFIX)
        return cls(
            q_value=q_value,
            label=project["projectLabel"],
            repo=GitLabRepo.from_url(project["repo"]),
        )


@dataclass(frozen=True)
class GitLabRepo:
    """The URL to a gitlab repository."""

    instance: str
    path: str

    @property
    def levels(self) -> list[str]:
        return self.path.split("/")

    @classmethod
    def from_url(cls, url: str) -> Self:
        """Parse from a gitlab URL in the form `https://<instance>/<path>`."""
        parsed = URL(url).with_scheme("https").with_fragment(None)
        if parsed.path.endswith(".git"):
            parsed = parsed.with_path(parsed.path[:-4])
        # remove a trailing slash
        # ok: https://api.gitlab.com/repos/simonmichael/hledger
        # not found: https://api.gitlab.com/repos/simonmichael/hledger/
        # https://www.wikidata.org/wiki/User_talk:Konstin#How_to_run_/_how_often_is_it_run?
        parsed = parsed.with_path(parsed.path.rstrip("/"))

        if not parsed.host or "/" not in parsed.path:
            raise InvalidProject(f"Invalid repo URL: {url}")
        # Ignore the trailing slash at the beginning of the path.
        return cls(parsed.host, parsed.path.removeprefix("/"))

    def __str__(self) -> str:
        return f"https://{self.instance}/{self.path}"

    def api_base(self) -> str:
        """The base gitlab api URL for the repository."""
        return f"https://{self.instance}/api/v4/projects/{quote(self.path)}"

    def api_releases(self) -> str:
        """The gitlab api URL for the releases of the repository."""
        return self.api_base() + "/releases"

    def api_tags(self) -> str:
        """The gitlab api URL for the tags of the repository."""
        return self.api_base() + "/repository/tags"
