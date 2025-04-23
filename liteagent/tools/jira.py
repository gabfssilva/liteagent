from typing import Optional, TYPE_CHECKING

from liteagent.internal import depends_on

if TYPE_CHECKING:
    from atlassian import Jira

from liteagent import Tools, tool


class JiraTools(Tools):
    client: 'Jira'

    def __init__(self, client: 'Jira'):
        self.client = client

    @tool(emoji="🔍")
    def search_issues(self, jql: str, limit: int = 25):
        """
        Search Jira issues using a JQL query.

        How to use:
        -----------
        This method lets you run JQL (Jira Query Language) to retrieve issues filtered by custom criteria.

        JQL supports filtering by fields such as:
            - project, issueType, priority
            - status, resolution, fixVersion
            - created, updated, due
            - assignee, reporter, labels, custom fields

        ### Working with the `assignee` field:

        You can match assignees using:
          • **Exact match**:
            `assignee = "John Doe"`
            `assignee = "john.doe@example.com"` *(cloud may require accountId instead)*

          • **Account ID** (preferred in Jira Cloud):
            `assignee = 5b10a2844c20165700ede21g`

          • **Dynamic function**:
            `assignee = currentUser()`

          • **Unassigned issues**:
            `assignee is EMPTY`

          • **Multiple users**:
            `assignee IN ("John Doe", "Jane Smith")`

          • **Partial match (if enabled)**:
            `assignee ~ "john"` *(matches name or email fragment)*

        ### Other useful fields and examples:

        - All open bugs in a project:
            `project = BUGS AND status != Done AND issuetype = Bug`

        - Issues created in the last 7 days:
            `created >= -7d`

        - Issues updated by a specific user:
            `updatedBy = "john.doe@example.com"`

        - Issues with a specific label:
            `labels = "infra"`

        - Full-text search in summary or description:
            `summary ~ "timeout"`
            `description ~ "performance degradation"`

        ### Example usage:

            tools.search_issues(
                jql='project = "ENG" AND assignee in (currentUser(), "john.doe@example.com") AND status != Done',
                limit=10
            )

        Notes:
            - Strings with spaces must be quoted.
            - Use `IN`, `=`, `!=`, `~`, `!~`, `IS EMPTY`, and `IS NOT EMPTY` to construct expressive queries.
            - Functions like `startOfDay()`, `endOfWeek()`, `currentUser()`, and `membersOf()` are supported.
        """
        issues = self.client.jql(jql, limit=limit).get("issues", [])

        return [{
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
            "assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else None,
            "assigneeEmail": issue["fields"]["assignee"]["emailAddress"] if issue["fields"]["assignee"] else None,
            "reporter": issue["fields"]["reporter"]["displayName"] if issue["fields"]["reporter"] else None,
            "created": issue["fields"]["created"],
            "updated": issue["fields"]["updated"],
            "url": f"{self.client.url}/browse/{issue['key']}",
            "description": issue["fields"].get("description", ""),
        } for issue in issues]

    @tool(emoji="🔍")
    def get_issue(self, issue_key: str) -> dict:
        """
        Retrieve detailed information for a single Jira issue.
        """
        issue = self.client.issue(issue_key)
        return {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
            "assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else None,
            "description": issue["fields"].get("description"),
            "url": f"{self.client.url}/browse/{issue['key']}",
            "created": issue["fields"]["created"],
            "updated": issue["fields"]["updated"],
            "comments": [c["body"] for c in issue["fields"].get("comment", {}).get("comments", [])]
        }

    @tool(emoji="🐛")
    def create_issue(self, project: str, summary: str, description: str, issuetype: str) -> str:
        """ Create a new issue in Jira. """
        issue = self.client.create_issue(fields={
            "project": {"key": project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issuetype}
        })
        return issue["key"]

    @tool(emoji="🎭")
    def transition_issue(self, issue_key: str, transition_name: str):
        """
        Transition an issue to a new state.
        """
        transitions = self.client.get_issue_transitions(issue_key)
        target = next((t for t in transitions if str(t["name"]).lower() == transition_name.lower()), None)
        if not target:
            raise ValueError(f"No transition named '{transition_name}' found.")

        self.client.issue_transition(issue_key, target["name"])

    @tool(emoji="📝")
    def add_comment(self, issue_key: str, comment: str):
        """
        Add a comment to a Jira issue.
        """
        self.client.issue_add_comment(issue_key, comment)

    @tool(emoji="📝")
    def assign_issue(self, issue_key: str, account_id: str):
        """
        Assign a Jira issue to a user.
        """
        self.client.assign_issue(issue_key, account_id)

    @tool(emoji="🔍")
    def get_project_issues(self, project_key: str, status: Optional[str], issuetype: Optional[str], limit: int = 50):
        """
        Retrieve issues from a project with optional filtering.
        """
        filters = [f'project = "{project_key}"']
        if status:
            filters.append(f'status = "{status}"')
        if issuetype:
            filters.append(f'issuetype = "{issuetype}"')
        return self.search_issues(" AND ".join(filters), limit=limit)

    @tool(emoji="🔍")
    def get_user_info(self, query: str) -> list[dict]:
        """
        Fetch information about a Jira user.
        """
        return self.client.user_find_by_user_string(query=query)

    @tool(emoji="🔍")
    def search_projects(self, names: list[str]):
        """
        Search for projects based on their names.
        """
        self.client.get_all_projects()


@depends_on({
    "atlassian": "atlassian-python-api"
})
def jira(client: 'Jira') -> Tools:
    return JiraTools(client=client)
