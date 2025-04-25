import asyncio
from typing import Optional, TYPE_CHECKING, Literal, List

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

    @tool(emoji="⏱️")
    def project_lead_time(self, project_key: str, days: int = 30) -> dict:
        """
        Calculate average lead time (created → resolved) for issues in a project.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d AND resolutiondate IS NOT EMPTY'
        issues = self.client.jql(jql, limit=1000).get("issues", [])

        import datetime
        lead_times = []

        for issue in issues:
            created = issue["fields"].get("created")
            resolved = issue["fields"].get("resolutiondate")
            if created and resolved:
                dt_created = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                dt_resolved = datetime.datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                lead_times.append((dt_resolved - dt_created).total_seconds() / 3600)  # hours

        return {
            "issue_count": len(lead_times),
            "average_lead_time_hours": round(sum(lead_times) / len(lead_times), 2) if lead_times else None
        }

    @tool(emoji="🔄")
    def project_cycle_time(self, project_key: str, days: int = 30, started_status: str = "In Progress") -> dict:
        """
        Estimate cycle time by checking when issues transitioned to 'In Progress' and were resolved.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d AND resolutiondate IS NOT EMPTY'
        issues = self.client.jql(jql, limit=1000, expand="changelog").get("issues", [])

        import datetime
        cycle_times = []

        for issue in issues:
            changelog = issue.get("changelog", {}).get("histories", [])
            start_time = None

            for entry in changelog:
                for item in entry.get("items", []):
                    if item["field"] == "status" and item["toString"] == started_status:
                        start_time = entry["created"]
                        break
                if start_time:
                    break

            resolved = issue["fields"].get("resolutiondate")
            if start_time and resolved:
                dt_started = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                dt_resolved = datetime.datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                cycle_times.append((dt_resolved - dt_started).total_seconds() / 3600)

        return {
            "issue_count": len(cycle_times),
            "average_cycle_time_hours": round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else None
        }

    @tool(emoji="🐌")
    def bottleneck_stages(self, project_key: str, days: int = 30, threshold_hours: float = 48.0) -> dict:
        """
        Identify bottleneck workflow stages where issues spend more time than a threshold.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self.client.jql(jql, limit=1000, expand="changelog").get("issues", [])

        from collections import defaultdict
        import datetime

        stage_times = defaultdict(list)

        for issue in issues:
            changelog = issue.get("changelog", {}).get("histories", [])
            previous_time = datetime.datetime.fromisoformat(issue["fields"]["created"].replace("Z", "+00:00"))
            previous_status = "Created"

            for change in changelog:
                change_time = datetime.datetime.fromisoformat(change["created"].replace("Z", "+00:00"))
                for item in change["items"]:
                    if item["field"] == "status":
                        time_spent = (change_time - previous_time).total_seconds() / 3600
                        stage_times[previous_status].append(time_spent)
                        previous_time = change_time
                        previous_status = item["toString"]

        # Average time in each status
        return {
            status: {
                "average_hours": round(sum(times)/len(times), 2),
                "count": len(times),
                "is_bottleneck": (sum(times)/len(times)) > threshold_hours
            }
            for status, times in stage_times.items()
        }

    @tool(emoji="📈")
    def throughput(self, project_key: str, days: int = 30) -> dict:
        """
        Count how many issues were resolved in the last X days.
        """
        jql = f'project = "{project_key}" AND resolutiondate >= -{days}d'
        issues = self.client.jql(jql, limit=1000).get("issues", [])
        return {
            "resolved_issues": len(issues),
            "start": f"-{days}d",
            "end": "now"
        }

    @tool(emoji="🔁")
    def reopen_rate(self, project_key: str, days: int = 90) -> dict:
        """
        Calculate the percentage of issues that were reopened after being resolved.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self.client.jql(jql, limit=1000, expand="changelog").get("issues", [])

        reopened_count = 0
        resolved_count = 0

        for issue in issues:
            changelog = issue.get("changelog", {}).get("histories", [])
            reopened = False
            resolved = False

            for entry in changelog:
                for item in entry.get("items", []):
                    if item["field"] == "status":
                        to_status = item.get("toString", "").lower()
                        if to_status in ["done", "resolved", "closed"]:
                            resolved = True
                        if to_status == "reopened":
                            reopened = True

            if resolved:
                resolved_count += 1
                if reopened:
                    reopened_count += 1

        return {
            "resolved_issues": resolved_count,
            "reopened_issues": reopened_count,
            "reopen_rate_percent": round((reopened_count / resolved_count) * 100, 2) if resolved_count else None
        }

    @tool(emoji="📊")
    def average_stage_count(self, project_key: str, days: int = 30) -> dict:
        """
        Estimate how many workflow stages each issue passes through on average.
        """
        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self.client.jql(jql, limit=1000, expand="changelog").get("issues", [])

        stage_counts = []

        for issue in issues:
            changelog = issue.get("changelog", {}).get("histories", [])
            statuses = set()

            for entry in changelog:
                for item in entry.get("items", []):
                    if item["field"] == "status":
                        statuses.add(item["toString"])

            stage_counts.append(len(statuses))

        return {
            "issue_count": len(stage_counts),
            "average_stage_transitions": round(sum(stage_counts) / len(stage_counts), 2) if stage_counts else None
        }

    @tool(emoji="⏰")
    def overdue_issues(self, project_key: str) -> list[dict]:
        """
        List issues that are past their due date.
        """
        import datetime

        jql = f'project = "{project_key}" AND duedate IS NOT EMPTY AND statusCategory != Done'
        issues = self.client.jql(jql, limit=1000).get("issues", [])

        overdue = []
        now = datetime.datetime.utcnow()

        for issue in issues:
            due = issue["fields"].get("duedate")
            if due:
                due_date = datetime.datetime.fromisoformat(due)
                if due_date < now:
                    overdue.append({
                        "key": issue["key"],
                        "summary": issue["fields"]["summary"],
                        "due_date": due_date.isoformat(),
                        "url": f"{self.client.url}/browse/{issue['key']}"
                    })

        return overdue


    @tool(emoji="📉")
    def delivery_predictability(self, project_key: str, days: int = 60) -> dict:
        """
        Compute standard deviation of lead time to measure delivery consistency.
        """
        import datetime
        import statistics

        jql = f'project = "{project_key}" AND created >= -{days}d AND resolutiondate IS NOT EMPTY'
        issues = self.client.jql(jql, limit=1000).get("issues", [])

        lead_times = []
        for issue in issues:
            created = issue["fields"].get("created")
            resolved = issue["fields"].get("resolutiondate")
            if created and resolved:
                dt_created = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                dt_resolved = datetime.datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                hours = (dt_resolved - dt_created).total_seconds() / 3600
                lead_times.append(hours)

        return {
            "issue_count": len(lead_times),
            "std_dev_lead_time_hours": round(statistics.stdev(lead_times), 2) if len(lead_times) > 1 else None
        }


    @tool(emoji="🔥")
    def burndown_trend(self, board_id: int, sprint_id: int) -> dict:
        """
        Retrieve burndown data for a specific sprint using the Agile API.
        """

        import datetime
        import re

        data = self.client.get(f'rest/greenhopper/1.0/rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}')
        if not data or "contents" not in data:
            raise ValueError("Invalid board or sprint ID.")

        completed = []
        estimate_field = data.get("contents", {}).get("completedIssuesInitialEstimateSum", {})
        if "text" in estimate_field:
            completed.append({"day": "end", "estimate": estimate_field["text"]})

        issues = data["contents"].get("completedIssues", [])
        trend = []

        for issue in issues:
            est = issue.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0)
            key = issue.get("key")
            trend.append({"issue": key, "estimate": est})

        return {
            "sprint": data["sprint"]["name"],
            "start_date": data["sprint"].get("startDate"),
            "end_date": data["sprint"].get("endDate"),
            "completed_estimate": completed,
            "burndown_issues": trend
        }

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

    @tool(emoji="🧮")
    def cumulative_flow_data(self, project_key: str, days: int = 30) -> list[dict]:
        """
        Prepare cumulative flow data: how many issues were in each status per day.
        """
        import datetime
        from collections import defaultdict, Counter

        end_date = datetime.datetime.now(datetime.UTC)
        start_date = end_date - datetime.timedelta(days=days)
        jql = f'project = "{project_key}" AND created >= -{days}d'
        issues = self.client.jql(jql, limit=1000, expand="changelog").get("issues", [])

        daily_status = defaultdict(lambda: Counter())

        for issue in issues:
            created = datetime.datetime.fromisoformat(issue["fields"]["created"].replace("Z", "+00:00"))
            changelog = issue.get("changelog", {}).get("histories", [])

            # Build timeline of status changes
            timeline = [(created, issue["fields"]["status"]["name"])]
            for change in changelog:
                for item in change.get("items", []):
                    if item["field"] == "status":
                        change_time = datetime.datetime.fromisoformat(change["created"].replace("Z", "+00:00"))
                        timeline.append((change_time, item["toString"]))

            timeline.sort()

            current_status = timeline[0][1]
            for i in range(days + 1):
                day = start_date + datetime.timedelta(days=i)
                for t, s in timeline:
                    if t.date() <= day.date():
                        current_status = s
                    else:
                        break
                daily_status[day.date()][current_status] += 1

        return [{
            "date": day.isoformat(),
            "status_counts": dict(counter)
        } for day, counter in sorted(daily_status.items())]

    @tool(emoji="📊")
    async def project_metrics_summary(
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
    ) -> dict:
        """
        Fetch multiple project metrics concurrently in a single call.
        """
        tasks = {}

        if "cumulative_flow_data" in metrics:
            tasks["cumulative_flow_data"] = self.cumulative_flow_data(project_key=project_key, days=days)
        if "lead_time" in metrics:
            tasks["lead_time"] = self.project_lead_time(project_key=project_key, days=days)
        if "cycle_time" in metrics:
            tasks["cycle_time"] = self.project_cycle_time(project_key=project_key, days=days, started_status=started_status)
        if "throughput" in metrics:
            tasks["throughput"] = self.throughput(project_key=project_key, days=days)
        if "delivery_predictability" in metrics:
            tasks["delivery_predictability"] = self.delivery_predictability(project_key=project_key, days=days)
        if "bottleneck_stages" in metrics:
            tasks["bottleneck_stages"] = self.bottleneck_stages(project_key=project_key, days=days, threshold_hours=threshold_hours)
        if "reopen_rate" in metrics:
            tasks["reopen_rate"] = self.reopen_rate(project_key=project_key, days=days)
        if "overdue_issues" in metrics:
            tasks["overdue_issues"] = self.overdue_issues(project_key=project_key)
        if "average_stage_count" in metrics:
            tasks["average_stage_count"] = self.average_stage_count(project_key=project_key, days=days)

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {name: result for name, result in zip(tasks.keys(), results)}

@depends_on({ "atlassian": "atlassian-python-api" })
def jira(client: 'Jira') -> Tools:
    return JiraTools(client=client)
