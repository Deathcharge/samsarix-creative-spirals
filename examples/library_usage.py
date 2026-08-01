"""Build and export the example campaign through the public Python API."""

from pathlib import Path

from samsarix_creative_spirals import build_campaign, check_campaign, export_campaign, load_campaign


def main() -> None:
    config = load_campaign(Path(__file__).with_name("campaign.json"))
    bundle = build_campaign(config)
    report = check_campaign(bundle)
    if not report.publishable:
        raise SystemExit("Campaign failed quality checks; preview it before export.")
    destination = export_campaign(bundle, "outbox")
    print(f"Checked and exported {len(bundle.drafts)} drafts to {destination}")


if __name__ == "__main__":
    main()
