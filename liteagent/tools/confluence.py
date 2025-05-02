from typing import Optional, TYPE_CHECKING, Literal

from pydantic import Field

if TYPE_CHECKING:
    from atlassian import Confluence

from liteagent import Tools, tool, ToolDef
from liteagent.internal import depends_on


class ConfluenceTools(Tools):
    client: 'Confluence'

    def __init__(self, client: 'Confluence'):
        self.client = client

    @tool(emoji="🔍")
    def confluence_search(self, cql: str):
        """
        Search Confluence pages using a CQL query.
        """
        response = self.client.cql(cql,
                                   expand='content.history,content.history.contributors,content.history.contributors.publishers.users,content.version,content.body.view,content.metadata,content.metadata.currentuser,content.metadata.simple')
        results = response['results']

        import markdownify

        return [{
            "id": result["content"]["id"],
            "type": result["content"]["type"],
            "status": result["content"]["status"],
            "title": result["content"]["title"],
            "excerpt": result["excerpt"],
            "url": f'{self.client.url}{result["url"]}',
            "body": markdownify.markdownify(result["content"]["body"]["view"]["value"]),
            "version": {
                "number": result["content"]["version"]["number"],
                "when": result["content"]["version"]["when"],
                "author": {
                    "accountId": result["content"]["version"]["by"]['accountId'],
                    "name": result["content"]["version"]["by"]['displayName'],
                    "email": result["content"]["version"]["by"]['email'],
                    "accountStatus": result["content"]["version"]["by"]['accountStatus']
                },
            },
            "authors": [{
                "accountId": user['accountId'],
                "name": user['displayName'],
                "email": user['email'],
                "accountStatus": user['accountStatus']
            } for user in result["content"]["history"]["contributors"]['publishers']["users"]]
        } for result in results]

    @tool(emoji="🔍")
    def get_page_by_id(self, page_id: str) -> dict:
        """
        Retrieve a Confluence page by its ID.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage,version")
        return {
            "id": page["id"],
            "title": page["title"],
            "body": page["body"]["storage"]["value"],
            "version": page["version"]["number"],
        }

    @tool(emoji="📝")
    def list_pages(
        self,
        space: str,
        limit: int | None,
    ):
        """ Retrieve the pages from a specific space """

        pages = self.client.get_all_pages_from_space(space, start=0, limit=limit, expand='version')

        for page in pages:
            yield {
                "id": page["id"],
                "title": page["title"],
                "parent_id": page["ancestors"][0]["id"] if page["ancestors"] else None,
                "version": page["version"]["number"],
            }

    @tool(emoji="📝")
    def create_page(self, space: str, title: str, body: str, parent_id: Optional[str]) -> dict:
        """
        Create a new Confluence page.
        """
        return self.client.create_page(space, title, body, parent_id=parent_id, type="page", representation="storage")

    @tool(emoji="📝")
    def append_to_page(self, page_id: str, content: str, version: int) -> dict:
        """
        Append content to the end of an existing Confluence page.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage,version")
        existing_body = page["body"]["storage"]["value"]
        updated_body = existing_body + content
        current_version = page["version"]["number"]

        if version != current_version:
            return {
                "message": "The provided version does not match the current version of the page. Fetch the page again and re-do the operation."}

        return self.client.update_page(page_id, page["title"], updated_body, representation="storage")

    @tool(emoji="📝")
    def update_title(self, page_id: str, title: str, version: int) -> dict:
        """
        Update the title of a specific confluence page.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage,version")

        current_version = page["version"]["number"]

        if version != current_version:
            return {
                "message": "The provided version does not match the current version of the page. Fetch the page again and re-do the operation."}

        return self.client.update_existing_page(page_id, title, page["body"]["storage"]["value"])

    @tool(emoji="📝")
    def update_page(self, page_id: str, old: str, new: str, version: int) -> dict:
        """
        Replace a specific string in the page body and update the page.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage,version")

        current_version = page["version"]["number"]

        if version != current_version:
            return {
                "message": "The provided version does not match the current version of the page. Fetch the page again and re-do the operation."}

        existing_body = page["body"]["storage"]["value"]
        updated_body = existing_body.replace(old, new)

        return self.client.update_page(page_id, page["title"], updated_body, representation="storage")

    @tool(emoji="📝")
    def add_comment_to_page(self, page_id: str, comment: str) -> dict:
        """
        Add a comment to a Confluence page.
        """
        return self.client.add_comment(page_id, comment)

    @tool(emoji="🔍")
    def get_user_info(self, account_id: str) -> dict:
        """
        Retrieve information about a Confluence user.
        """
        return self.client.get(f"/rest/api/user?accountId={account_id}")

    @tool(emoji='📋')
    def search_spaces_by_name(
        self,
        space_type: Literal['global', 'personal'] | None = Field(..., description="Space type. If none, defaults to 'global'."),
        space_status: Literal['current', 'archived'] | None = Field(..., description="Space status. If none, defaults to 'current'."),
        contains_one_of: list[str] = Field(..., description="A list of strings used to filter spaces by name."),
    ):
        """Retrieve information about spaces based on their name."""
        space_type = space_type or 'global'
        space_status = space_status or 'current'

        cursor = 0
        page_size = 50

        while True:
            result = self.client.get_all_spaces(
                start=cursor,
                limit=page_size,
                space_type=space_type,
                space_status=space_status,
                expand='description.plain'
            )

            spaces = result['results']

            has_next = spaces['_links'].get('next', None)

            if not has_next:
                break

            for space in spaces:
                name = space['name']

                if any(matching_name.lower() in name.lower() for matching_name in contains_one_of):
                    yield {
                        "id": space['id'],
                        "name": name,
                        "key": space['key'],
                    }

            cursor = cursor + page_size

@depends_on({
    "atlassian": "atlassian-python-api"
})
def confluence(client: 'Confluence') -> ToolDef:
    return ConfluenceTools(client=client)
