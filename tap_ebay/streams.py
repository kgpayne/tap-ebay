"""Stream type classes for tap-ebay."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ebaysdk.response import ResponseDataObject

from tap_ebay.client import eBayStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class FindingStream(eBayStream):
    """Define custom stream."""

    name = "finding_items"
    primary_keys = ["itemId"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "finding_item.json"

    def __init__(
        self,
        *args,
        searches: list,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.searches = searches
        self._api = None

    @property
    def api(self):
        if self._api is None:
            self._api = self.client.get_finding_api()
        return self._api

    @classmethod
    def response_to_dict(cls, obj):
        if isinstance(obj, ResponseDataObject):
            obj = obj.__dict__
            for key, value in obj.items():
                obj[key] = cls.response_to_dict(value)
        return obj

    @staticmethod
    def get_all_items(client, api, verb, data, max_pages=100):
        items = []
        params = deepcopy(data)
        params["paginationInput"] = {"entriesPerPage": 100}
        response = client.execute(api, verb, params)
        if hasattr(response.reply.searchResult, "item"):
            items.extend(response.reply.searchResult.item)
        page_number = int(response.reply.paginationOutput.pageNumber)
        total_pages = int(response.reply.paginationOutput.totalPages)
        while (page_number < total_pages) and (page_number < max_pages):
            page_number += 1
            params["paginationInput"] = {
                "entriesPerPage": 100,
                "pageNumber": page_number,
            }
            response = client.execute(api, verb, params)
            if hasattr(response.reply.searchResult, "item"):
                items.extend(response.reply.searchResult.item)
        return items

    def get_records(self, context: dict | None):
        for search in self.searches:
            items = self.get_all_items(
                client=self.client,
                api=self.api,
                verb=search["verb"],
                data=search["data"],
                max_pages=search.get("max_pages", 100),
            )
            for item in items:
                record = self.response_to_dict(item)
                record["search_id"] = search["name"]
                yield record
