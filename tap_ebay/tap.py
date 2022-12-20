"""eBay tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_ebay.client import eBayClient
from tap_ebay.streams import FindingStream


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
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        client = eBayClient(app_id=self.config["app_id"])
        return [
            FindingStream(
                tap=self,
                name=search["name"],
                client=client,
                verb=search["verb"],
                data=search.get("data", {}),
                max_pages=search["max_pages"],
            )
            for search in self.config.get("searches", [])
        ]


if __name__ == "__main__":
    TapeBay.cli()
