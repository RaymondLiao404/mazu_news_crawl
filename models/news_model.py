from dataclasses import dataclass


@dataclass
class NewsFeedEntry:
    title: str
    link: str
    published_at: str


@dataclass
class NewsItem:
    title: str
    link: str
    published_at: str
