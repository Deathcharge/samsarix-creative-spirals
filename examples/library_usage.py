"""Build and export the example campaign through the public Python API."""

from pathlib import Path

from helix_creative_spirals import build_campaign, export_campaign, load_campaign


def main() -> None:
    config = load_campaign(Path(__file__).with_name("campaign.json"))
    bundle = build_campaign(config)
    destination = export_campaign(bundle, "outbox")
    print(f"Exported {len(bundle.drafts)} drafts to {destination}")


if __name__ == "__main__":
    main()
