import asyncpraw
from typing import List, Union

from liteagent import tool, Tools


class Reddit(Tools):
    def __init__(self, client_id: Union[str, None], client_secret: Union[str, None], user_agent: Union[str, None]):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent if user_agent else "liteagent:reddit_tool:v1.0"

        self.reddit = None
        if client_id and client_secret:
            self.reddit_kwargs = {
                "client_id": client_id,
                "client_secret": client_secret,
                "user_agent": self.user_agent
            }
        else:
            self.reddit_kwargs = None

    async def _get_reddit(self):
        """Get or create AsyncPRAW Reddit instance."""
        if not self.reddit_kwargs:
            return None

        if not self.reddit:
            self.reddit = asyncpraw.Reddit(**self.reddit_kwargs)

        return self.reddit

    @tool(emoji='🔍')
    async def search(
        self,
        query: str,
        subreddit: Union[str, None],
        limit: Union[int, None],
        sort: Union[str, None]
    ) -> List[dict]:
        """
        Search Reddit for posts matching the given query.
        """
        reddit = await self._get_reddit()
        if not reddit:
            return [{"error": "Reddit credentials not provided. Initialize with client_id and client_secret."}]

        if limit is None:
            limit = 10

        if sort is None:
            sort = "relevance"

        try:
            if subreddit:
                sub = await reddit.subreddit(subreddit)
                results = sub.search(query, sort=sort, limit=limit)
            else:
                results = await reddit.subreddit("all")
                results = results.search(query, sort=sort, limit=limit)

            posts = []
            async for post in results:
                posts.append({
                    "title": post.title,
                    "author": post.author.name if post.author else "[deleted]",
                    "subreddit": post.subreddit.display_name,
                    "score": post.score,
                    "created_utc": post.created_utc,
                    "url": post.url,
                    "permalink": f"https://reddit.com{post.permalink}",
                    "num_comments": post.num_comments,
                    "is_self": post.is_self
                })

                if len(posts) >= limit:
                    break

            return posts

        except Exception as e:
            return [{"error": str(e)}]

    @tool(emoji='📋')
    async def get_subreddit_posts(
        self,
        subreddit: str,
        category: Union[str, None],
        limit: Union[int, None],
        time_filter: Union[str, None]
    ) -> List[dict]:
        """
        Get posts from a specific subreddit.
        """
        reddit = await self._get_reddit()
        if not reddit:
            return [{"error": "Reddit credentials not provided. Initialize with client_id and client_secret."}]

        if category is None:
            category = "hot"

        if limit is None:
            limit = 10

        if time_filter is None:
            time_filter = "all"

        try:
            sub = await reddit.subreddit(subreddit)
            posts_generator = None

            if category == "hot":
                posts_generator = sub.hot(limit=limit)
            elif category == "new":
                posts_generator = sub.new(limit=limit)
            elif category == "top":
                posts_generator = sub.top(time_filter=time_filter, limit=limit)
            elif category == "rising":
                posts_generator = sub.rising(limit=limit)
            elif category == "controversial":
                posts_generator = sub.controversial(time_filter=time_filter, limit=limit)
            else:
                return [{"error": f"Invalid category: {category}"}]

            posts = []
            async for post in posts_generator:
                posts.append({
                    "title": post.title,
                    "author": post.author.name if post.author else "[deleted]",
                    "score": post.score,
                    "created_utc": post.created_utc,
                    "url": post.url,
                    "permalink": f"https://reddit.com{post.permalink}",
                    "num_comments": post.num_comments,
                    "is_self": post.is_self
                })

                if len(posts) >= limit:
                    break

            return posts

        except Exception as e:
            return [{"error": str(e)}]

    @tool(emoji='💬')
    async def get_post_comments(
        self,
        post_id: str,
        sort: Union[str, None],
        limit: Union[int, None]
    ) -> List[dict]:
        """
        Get comments from a specific Reddit post.
        """
        reddit = await self._get_reddit()
        if not reddit:
            return [{"error": "Reddit credentials not provided. Initialize with client_id and client_secret."}]

        if sort is None:
            sort = "top"

        if limit is None:
            limit = 10

        try:
            if post_id.startswith('t3_'):
                post_id = post_id[3:]

            submission = await reddit.submission(id=post_id)

            # Set comment sort
            submission.comment_sort = sort if sort in ["top", "best", "new", "controversial", "old"] else "top"

            # Load comments
            await submission.load()
            await submission.comments.replace_more(limit=0)  # Remove "load more comments" objects

            comments = []
            for comment in submission.comments[:limit]:
                comments.append({
                    "author": comment.author.name if hasattr(comment, 'author') and comment.author else "[deleted]",
                    "body": comment.body,
                    "score": comment.score,
                    "created_utc": comment.created_utc,
                    "permalink": f"https://reddit.com{comment.permalink}",
                    "id": comment.id
                })

            return comments

        except Exception as e:
            return [{"error": str(e)}]


def reddit(
    client_id: Union[str, None] = None,
    client_secret: Union[str, None] = None,
    user_agent: Union[str, None] = None
) -> Reddit:
    return Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
