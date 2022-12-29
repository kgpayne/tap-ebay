"""eBay tap class."""

import csv
import glob
from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_ebay.client import eBayClient
from tap_ebay.streams import FindingStream, ItemStatusStream


class TapeBay(Tap):
    """eBay tap class."""

    name = "tap-ebay"
    config_jsonschema = th.PropertiesList(
        th.Property(
            "app_id",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            description="The App ID to use to authenticate against the API service",
        ),
        th.Property(
            "client_secret",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            description="The Client Secret to use to authenticate against the API service",
        ),
        th.Property(
            "redirect_uri",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            default="http://localhost/",
            description="The Client Secret to use to authenticate against the API service",
        ),
        th.Property(
            "searches",
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType, required=True),
                    th.Property("verb", th.StringType, required=True),
                    th.Property("data", th.ObjectType(), required=False),
                    th.Property(
                        "max_pages", th.IntegerType, required=False, default=100
                    ),
                )
            ),
        ),
        th.Property(
            "item_status_file_path",
            th.StringType,
            description="File path to items list CSV.",
            required=False,
        ),
        th.Property(
            "item_status_file_pattern",
            th.StringType,
            description="File glob pattern to items list CSV(s).",
            required=False,
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        client = eBayClient(
            app_id=self.config["app_id"],
            client_secret=self.config["client_secret"],
            redirect_uri=self.config["redirect_uri"],
        )
        # Finding Stream
        streams = (
            [FindingStream(tap=self, client=client, searches=self.config["searches"])]
            if "searches" in self.config
            else []
        )
        # Item Status Stream
        if "item_status_file_path" in self.config:
            # assume file path is file
            with open(self.config["item_status_file_path"]) as f:
                records = csv.reader(f)
                items = [i[0] for i in list(records)[1:]]

        if "item_status_file_pattern" in self.config:
            files = glob.glob(
                self.config["item_status_file_pattern"],
            )
            items = []
            for file in files:
                with open(file) as f:
                    records = csv.reader(f)
                    items.extend([i[0] for i in list(records)[1:]])

        streams.append(
            ItemStatusStream(tap=self, client=client, items=list(set(items)))
        )

        return streams


if __name__ == "__main__":
    TapeBay.cli()
