"""Custom client handling, including eBayStream base class."""

from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import singer_sdk._singerlib as singer
from ebaysdk.exception import ConnectionError
from ebaysdk.finding import Connection as Finding
from singer_sdk.streams import Stream

logger = logging.getLogger(__name__)


class eBayClient:
    def __init__(self, app_id):
        self.app_id = app_id

    def get_finding_api(self):
        return Finding(appid=self.app_id, config_file=None)

    def execute(self, api, verb, data: dict = {}):
        try:
            return api.execute(verb, data)
        except ConnectionError as e:
            logger.error(f"Connection failed: {e}\n{e.response.dict()}")
            raise e


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
