import datetime
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING, Literal, List, Counter, Any, TypedDict

from liteagent.internal import depends_on

if TYPE_CHECKING:
    from atlassian import Jira

from liteagent import Tools, tool


@dataclass
class ChangeLogEntry:
    field: str
    from_: Optional[str]
    to: Optional[str]
    changed_at: str
    author: Optional[str]

@dataclass
class Issue:
    key: str
    summary: str
    status: str
    status_category: str
    assignee: Optional[str]
    assigneeEmail: Optional[str]
    reporter: Optional[str]
    created: str
    updated: str
    duedate: Optional[str]
    url: str
    description: str
    changelog: List[ChangeLogEntry]
    comments: List[str]

    def is_overdue(self, now = datetime.datetime.now(datetime.timezone.utc)) -> bool:
        if not self.duedate:
            return False

        due_date = datetime.datetime.fromisoformat(self.duedate + "T00:00:00").replace(tzinfo=datetime.timezone.utc)
        return due_date < now and self.status_category.lower() != "done"

    @classmethod
    def from_sdk(cls, issue: dict) -> 'Issue':
        def extract_changelog():
            for history in issue.get("changelog", {}).get("histories", []):
                for item in history.get("items", []):
                    yield ChangeLogEntry(
                        field=item.get("field"),
                        from_=item.get("fromString"),
                        to=item.get("toString"),
                        changed_at=history.get("created"),
                        author=history.get("author", {}).get("displayName")
                    )

        return cls(
            key=issue["key"],
            summary=issue["fields"]["summary"],
            status=issue["fields"]["status"]["name"],
            status_category=issue["fields"]["status"]["statusCategory"]["key"],
            assignee=issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else None,
            assigneeEmail=issue["fields"]["assignee"].get("emailAddress") if issue["fields"].get("assignee") else None,
            reporter=issue["fields"]["reporter"]["displayName"] if issue["fields"].get("reporter") else None,
            created=issue["fields"]["created"],
            updated=issue["fields"]["updated"],
            duedate=issue["fields"]["duedate"],
            url=f"{issue['self'].split('/rest/')[0]}/browse/{issue['key']}",
            description=issue["fields"].get("description", ""),
            changelog=list(extract_changelog()),
            comments=[
                c["body"] for c in issue["fields"].get("comment", {}).get("comments", [])
            ]
        )

@dataclass
class Issues:
    issues: List[Issue]
    now: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @staticmethod
    def _parse_dt(raw: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))

    @property
    def lead_times(self) -> List[float]:
        times = []
        for issue in self.issues:
            created = self._parse_dt(issue.created)
            resolved = next(
                (self._parse_dt(c.changed_at) for c in issue.changelog if c.field == "resolution" and c.to),
                None
            )
            if resolved:
                times.append((resolved - created).total_seconds() / 3600)
        return times

    def cycle_times(self, started_status: str = "In Progress") -> List[float]:
        times = []
        for issue in self.issues:
            start = next((self._parse_dt(c.changed_at) for c in issue.changelog if c.field == "status" and c.to == started_status), None)
            end = next((self._parse_dt(c.changed_at) for c in issue.changelog if c.field == "resolution" and c.to), None)
            if start and end:
                times.append((end - start).total_seconds() / 3600)
        return times

    @property
    def throughput(self) -> int:
        return sum(1 for i in self.issues if any(c.field == "resolution" and c.to for c in i.changelog))

    def bottleneck_stages(self, threshold_hours: float = 48.0) -> dict[str, dict]:
        stage_times = defaultdict(list)
        for issue in self.issues:
            last_time = self._parse_dt(issue.created)
            last_status = None
            for c in issue.changelog:
                if c.field == "status" and c.to:
                    now_time = self._parse_dt(c.changed_at)
                    if last_status:
                        stage_times[last_status].append((now_time - last_time).total_seconds() / 3600)
                    last_time = now_time
                    last_status = c.to
            if last_status:
                stage_times[last_status].append((self.now - last_time).total_seconds() / 3600)

        return {
            k: {
                "average_hours": round(sum(v) / len(v), 2),
                "count": len(v),
                "is_bottleneck": (sum(v) / len(v)) > threshold_hours
            }
            for k, v in stage_times.items()
        }

    @property
    def reopen_rate(self) -> dict:
        reopened = 0
        resolved = 0
        for issue in self.issues:
            was_closed = False
            reopened_later = False
            for c in issue.changelog:
                if c.field == "status":
                    to = (c.to or "").lower()
                    if to in {"done", "closed", "resolved"}:
                        was_closed = True
                    elif to == "reopened" and was_closed:
                        reopened_later = True
            if was_closed:
                resolved += 1
                if reopened_later:
                    reopened += 1
        return {
            "resolved_issues": resolved,
            "reopened_issues": reopened,
            "reopen_rate_percent": round((reopened / resolved) * 100, 2) if resolved else None
        }

    @property
    def average_stage_count(self) -> float:
        stage_counts = [
            len({c.to for c in i.changelog if c.field == "status" and c.to})
            for i in self.issues
        ]
        return round(sum(stage_counts) / len(stage_counts), 2) if stage_counts else 0.0

    def cumulative_flow_data(self, days: int, started_at: Optional[datetime.datetime] = None):
        started_at = started_at or self.now - datetime.timedelta(days=days)
        snapshots = defaultdict(lambda: Counter())
        for issue in self.issues:
            timeline = [(self._parse_dt(issue.created), issue.status)]
            for c in issue.changelog:
                if c.field == "status" and c.to:
                    timeline.append((self._parse_dt(c.changed_at), c.to))
            timeline.sort()
            for i in range(days + 1):
                day = (started_at + datetime.timedelta(days=i)).date()
                current = timeline[0][1]
                for t, s in timeline:
                    if t.date() <= day:
                        current = s
                    else:
                        break
                snapshots[day][current] += 1
        return [
            {"date": day.isoformat(), "status_counts": dict(counter)}
            for day, counter in sorted(snapshots.items())
        ]

    def overdue_issues(self) -> List[Issue]:
        return list(filter(lambda i: i.is_overdue(self.now), self.issues))

class JiraTools(Tools):
    client: 'Jira'

    def __init__(self, client: 'Jira'):
        self.client = client

    @tool(emoji="🔍")
    def search_issues(self, jql: str):
        """ Search Jira issues using a JQL query. """
        yield from self._paginated_issues(jql)

    @tool(emoji="🔍")
    def get_issue(self, issue_key: str) -> Issue | str:
        """ Retrieve a single Jira issue. """
        issue = self.client.issue(issue_key, expand="changelog")

        if not issue:
            return f"No issue with key '{issue_key}' found."

        return Issue.from_sdk(issue)

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

    @tool(emoji="📝")
    def update_issue(self, issue_key: str, fields: List[TypedDict("Content", {
        "field": Literal['summary', 'description'],
        "new_value": str,
    })]) -> str:
        """ Update an existing issue in Jira. """

        issue = self.client.issue(issue_key)
        if not issue:
            return f"No issue with key '{issue_key}' found."

        self.client.update_issue(
            issue_key=issue_key,
            update={
                "fields": { f["field"]: f["new_value"] for f in fields }
            }
        )

        return "Issue successfully updated."

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
    async def get_project_issues(
        self,
        project_key: str,
        status: Optional[str],
        issue_type: Optional[str],
        limit: int = 50
    ):
        """
        Retrieve issues from a project with optional filtering.
        """
        filters = [f'project = "{project_key}"']
        if status:
            filters.append(f'status = "{status}"')
        if issue_type:
            filters.append(f'issuetype = "{issue_type}"')

        return await self.search_issues(jql=" AND ".join(filters), limit=limit)

    @tool(emoji="🔍")
    def get_user_info(self, query: str) -> list[dict]:
        """
        Fetch information about a Jira user.
        """
        return self.client.user_find_by_user_string(query=query)

    @tool(emoji='📊')
    def project_metrics(
        self,
        project_key: str,
        metrics: List[Literal[
            "lead_time",
            "cycle_time",
            "throughput",
            "delivery_predictability",
            "bottleneck_stages",
            "reopen_rate",
            "overdue_issues",
            "average_stage_count",
            "cumulative_flow_data"
        ]],
        days: int = 30,
        started_status: str = "In Progress",
        threshold_hours: float = 48.0
    ) -> dict[str, dict]:
        """
        Extract the specified metrics for the given project.
        Before calling this tool, check the available statuses for the project via `list_project_statuses`.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        start_date = now - datetime.timedelta(days=days)

        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self._all_issues(jql)

        results: dict[str, Any] = {}

        for metric in metrics:
            match metric:
                case "lead_time":
                    values = issues.lead_times
                    results["lead_time"] = {
                        "issue_count": len(values),
                        "average_lead_time_hours": round(sum(values) / len(values), 2) if values else None
                    }

                case "delivery_predictability":
                    values = issues.lead_times
                    results["delivery_predictability"] = {
                        "issue_count": len(values),
                        "std_dev_lead_time_hours": round(statistics.stdev(values), 2) if len(values) > 1 else None
                    }

                case "cycle_time":
                    values = issues.cycle_times(started_status)
                    results["cycle_time"] = {
                        "issue_count": len(values),
                        "average_cycle_time_hours": round(sum(values) / len(values), 2) if values else None
                    }

                case "throughput":
                    results["throughput"] = {
                        "resolved_issues": issues.throughput,
                        "start": f"-{days}d",
                        "end": "now"
                    }

                case "bottleneck_stages":
                    results["bottleneck_stages"] = issues.bottleneck_stages(threshold_hours)

                case "reopen_rate":
                    results["reopen_rate"] = issues.reopen_rate

                case "overdue_issues":
                    results["overdue_issues"] = [
                        {
                            "key": i.key,
                            "summary": i.summary,
                            "due_date": f"{i.duedate}T00:00:00+00:00",
                            "url": i.url
                        }
                        for i in issues.overdue_issues()
                    ]

                case "average_stage_count":
                    results["average_stage_count"] = {
                        "issue_count": len(issues.issues),
                        "average_stage_transitions": issues.average_stage_count
                    }

                case "cumulative_flow_data":
                    results["cumulative_flow_data"] = issues.cumulative_flow_data(days, started_at=start_date)

                case _:
                    raise ValueError(f"Unknown metric: {metric}")

        return results

    @tool(emoji="📋")
    def list_project_statuses(self, project_key: str, days: int = 90) -> list[str]:
        """
        List all unique statuses (workflow states) used by issues in a project.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self.client.jql(jql, limit=1000).get("issues", [])

        statuses = {issue["fields"]["status"]["name"] for issue in issues}
        return sorted(statuses)

    @tool(emoji="📋")
    def list_sprints(self, project_key: str, state: Literal['active', 'closed', 'future']):
        """
        List sprints for all boards in a given project and state.
        """
        boards = self.client.get_all_agile_boards(project_key=project_key)

        results = {}

        for board in boards.get("values", []):
            board_id = board["id"]
            board_name = board["name"]

            sprints = self.client.get_all_sprint(board_id, state=state)
            sprint_list = [
                {
                    "id": sprint["id"],
                    "name": sprint["name"],
                    "state": sprint["state"],
                    "startDate": sprint.get("startDate"),
                    "endDate": sprint.get("endDate"),
                }
                for sprint in sprints.get("values", [])
            ]

            if sprint_list:
                results[board_name] = sprint_list

        return results

    def _all_issues(self, jql: str, expand: str = "changelog") -> Issues:
        return Issues(issues=list(self._paginated_issues(jql, expand)))

    def _paginated_issues(self, jql: str, expand: str = "changelog"):
        response = self.client.enhanced_jql(jql, expand=expand)
        issues = response.get("issues", [])

        for issue in issues:
            yield Issue.from_sdk(issue)


@depends_on({ "atlassian": "atlassian-python-api" })
def jira(client: 'Jira') -> Tools:
    return JiraTools(client=client)
