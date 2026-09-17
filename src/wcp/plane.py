"""Plane REST adapter and idempotent WCP projection."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from wcp.events import EntityType
from wcp.store import EventStore


class PlaneError(RuntimeError):
    pass


class PlaneAPI(Protocol):
    def list_states(self) -> list[dict[str, Any]]: ...

    def create_work_item(self, data: dict[str, Any]) -> dict[str, Any]: ...

    def update_work_item(
        self, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]: ...

    def create_comment(
        self, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PlaneClient:
    base_url: str
    api_key: str
    workspace_slug: str
    project_id: str
    timeout: float = 30.0

    @property
    def _project_path(self) -> str:
        return f"api/v1/workspaces/{self.workspace_slug}/projects/{self.project_id}"

    def _request(
        self, method: str, path: str, data: dict[str, Any] | None = None
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        body = json.dumps(data).encode() if data is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "wcp/0.1",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                raw = response.read()
        except HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise PlaneError(f"Plane returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise PlaneError(f"Could not reach Plane: {error.reason}") from error
        return json.loads(raw) if raw else {}

    def list_states(self) -> list[dict[str, Any]]:
        response = self._request("GET", f"{self._project_path}/states/")
        if isinstance(response, dict):
            return list(response.get("results", []))
        return list(response)

    def create_work_item(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"{self._project_path}/work-items/", data)

    def update_work_item(
        self, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PATCH", f"{self._project_path}/work-items/{work_item_id}/", data
        )

    def create_comment(self, work_item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"{self._project_path}/work-items/{work_item_id}/comments/",
            data,
        )


class PlaneProjector:
    """Project actionable WCP entities and concise milestones into Plane."""

    provider = "plane"

    def __init__(self, client: PlaneAPI) -> None:
        self.client = client

    def sync(self, store: EventStore, project_id: str) -> dict[str, int]:
        state_ids = self._state_ids()
        counts = {"created": 0, "updated": 0, "comments": 0}
        for entity_type in (EntityType.QUESTION, EntityType.EXPERIMENT):
            for aggregate in store.list(entity_type.value, project_id):
                payload = self._work_item_payload(store, aggregate, state_ids)
                reference = store.external_ref(
                    self.provider, entity_type.value, aggregate["id"]
                )
                if reference is None:
                    created = self.client.create_work_item(payload)
                    external_id = created.get("id")
                    if not isinstance(external_id, str) or not external_id:
                        raise PlaneError("Plane create response did not include an id")
                    store.link_external(
                        self.provider,
                        entity_type.value,
                        aggregate["id"],
                        external_id,
                        metadata={"sequence_id": created.get("sequence_id")},
                    )
                    counts["created"] += 1
                else:
                    external_id = reference["external_id"]
                    self.client.update_work_item(external_id, payload)
                    counts["updated"] += 1

        for event in store.events():
            if event.event_type.endswith(".created") or store.event_was_projected(
                self.provider, event.id
            ):
                continue
            reference = store.external_ref(
                self.provider, event.entity_type.value, event.entity_id
            )
            if reference is None:
                continue
            comment = self.client.create_comment(
                reference["external_id"], self._comment_payload(event)
            )
            store.mark_event_projected(self.provider, event.id, comment.get("id"))
            counts["comments"] += 1
        return counts

    def _state_ids(self) -> dict[str, str]:
        states = self.client.list_states()
        by_name = {
            str(state.get("name", "")).strip().lower(): str(state["id"])
            for state in states
            if state.get("id")
        }
        by_group: dict[str, str] = {}
        for state in states:
            group = str(state.get("group", "")).strip().lower()
            if group and state.get("id"):
                by_group.setdefault(group, str(state["id"]))

        desired_groups = {
            "proposed": "backlog",
            "framing": "unstarted",
            "ready": "unstarted",
            "investigating": "started",
            "awaiting-analysis": "started",
            "awaiting-decision": "started",
            "settled": "completed",
            "abandoned": "cancelled",
            "superseded": "cancelled",
            "planned": "unstarted",
            "launched": "started",
            "running": "started",
            "succeeded": "completed",
            "failed": "cancelled",
            "cancelled": "cancelled",
            "analyzed": "completed",
        }
        return {
            state: by_name.get(state, by_group.get(group, ""))
            for state, group in desired_groups.items()
        }

    def _work_item_payload(
        self,
        store: EventStore,
        aggregate: dict[str, Any],
        state_ids: dict[str, str],
    ) -> dict[str, Any]:
        data = aggregate["data"]
        title = str(data.get("title") or data.get("key") or aggregate["id"])
        key = data.get("key")
        name = f"[{key}] {title}" if key and not title.startswith(f"[{key}]") else title
        description = (
            f"<p><strong>WCP {aggregate['entity_type']}:</strong> "
            f"<code>{aggregate['id']}</code></p>"
            f"<p><strong>State:</strong> {html.escape(aggregate['state'])}</p>"
        )
        summary = data.get("question") or data.get("hypothesis") or data.get("summary")
        if summary:
            description += f"<p>{html.escape(str(summary))}</p>"
        payload: dict[str, Any] = {"name": name, "description_html": description}
        state_id = state_ids.get(aggregate["state"])
        if state_id:
            payload["state"] = state_id
        if aggregate["entity_type"] == EntityType.EXPERIMENT.value:
            question_id = data.get("question_id")
            if isinstance(question_id, str):
                parent = store.external_ref(
                    self.provider, EntityType.QUESTION.value, question_id
                )
                if parent:
                    payload["parent"] = parent["external_id"]
        return payload

    @staticmethod
    def _comment_payload(event: Any) -> dict[str, Any]:
        payload = html.escape(json.dumps(event.payload, sort_keys=True))
        content = (
            f"<p><strong>{html.escape(event.event_type)}</strong> by "
            f"{html.escape(event.actor_id)}</p><p><code>{payload}</code></p>"
            f"<p>WCP event: <code>{event.id}</code></p>"
        )
        return {
            "comment_html": content,
            "comment_json": {},
            "access": "INTERNAL",
            "external_source": "wcp",
            "external_id": event.id,
        }
