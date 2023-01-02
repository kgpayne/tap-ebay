"""Stream type classes for tap-ebay."""

from __future__ import annotations

from copy import deepcopy
from os import PathLike
from pathlib import Path
from typing import Any

import singer_sdk._singerlib as singer
from ebaysdk.response import ResponseDataObject
from singer_sdk.streams import Stream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class eBayStream(Stream):
    """Stream class for eBay streams."""

    def __init__(
        self,
        tap,
        client,
        schema: str | PathLike | dict[str, Any] | singer.Schema | None = None,
        name: str | None = None,
    ):
        super().__init__(tap=tap, schema=schema, name=name)
        self.client = client

    @classmethod
    def response_to_dict(cls, obj):
        if isinstance(obj, ResponseDataObject):
            obj = obj.__dict__
            for key, value in obj.items():
                obj[key] = cls.response_to_dict(value)
        return obj


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

    def get_api(self, site_id="EBAY-US"):
        return self.client.get_finding_api(site_id=site_id)

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
            for site_id in search.get("site_global_ids", ["EBAY-US"]):
                api = self.get_api(site_id=site_id)
                items = self.get_all_items(
                    client=self.client,
                    api=api,
                    verb=search["verb"],
                    data=search["data"],
                    max_pages=search.get("max_pages", 100),
                )
                for item in items:
                    record = self.response_to_dict(item)
                    record["search_id"] = search["name"]
                    yield record


class ItemStatusStream(eBayStream):

    name = "item_status"
    primary_keys = ["itemId"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "item_status.json"

    def __init__(
        self,
        *args,
        items: list[dict],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.items = items

    def get_api(self, site_id="EBAY-US"):
        return self.client.get_shopping_api(site_id=site_id)

    @staticmethod
    def get_item_status(client, api, verb, data, max_pages=100):
        params = deepcopy(data)
        params["paginationInput"] = {"entriesPerPage": 100}
        response = client.execute(api, verb, params)
        if hasattr(response.reply, "Item"):
            return response.reply.Item

    def get_records(self, context: dict | None):
        for item in self.items:
            api = self.get_api(site_id=item["site_id"])
            item_status = self.get_item_status(
                client=self.client,
                api=api,
                verb="GetItemStatus",
                data={"ItemID": item["id"]},
            )
            if item_status:
                item_status_dict = self.response_to_dict(item_status)
                yield item_status_dict
