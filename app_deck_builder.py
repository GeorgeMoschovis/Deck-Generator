"""
Local Deck Builder — pick which slides to include and choose a layout variant per slide type.

Run from the project root (after activating your venv):

    streamlit run app_deck_builder.py

Requires: pip install -r requirements.txt
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st
import yaml

from src.deck_pipeline import generate_deck
from src.slide_variants import (
    DEFAULT_VARIANTS,
    SLIDE_ORDER,
    SLIDE_VARIANT_GROUPS,
    default_enabled_slides,
)

PROJECT_ROOT = Path(__file__).resolve().parent
DECK_BUILDER_STATE_PATH = PROJECT_ROOT / ".deck_builder_state.json"


def _load_deck_builder_disk_state() -> dict:
    if not DECK_BUILDER_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(DECK_BUILDER_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_deck_builder_disk_state(data: dict) -> None:
    try:
        DECK_BUILDER_STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


SLIDE_LABELS: dict[str, str] = {
    "title": "Title",
    "performance_summary": "Performance summary",
    "exposure_sector": "Sector exposure",
    "exposure_geography": "Geographic exposure",
    "top_positions": "Top positions",
    "risk_metrics": "Risk metrics",
    "attribution": "P&L attribution",
    "disclaimer": "Disclaimer",
}

TEMPLATE_CHOICES: dict[str, Path | None] = {
    "Base config only": None,
    "Minimal investor": PROJECT_ROOT / "config" / "templates" / "minimal_investor.yaml",
    "Full GP report": PROJECT_ROOT / "config" / "templates" / "full_gp_report.yaml",
}


def _load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    st.set_page_config(page_title="Fund Deck Builder", layout="wide")
    st.title("Fund Deck Builder")
    st.caption("Choose slides and layouts, then generate a PowerPoint deck — runs entirely on your machine.")

    config_path = PROJECT_ROOT / "config" / "fund_config.yaml"
    if not config_path.exists():
        st.error(f"Config not found: {config_path}")
        st.stop()

    config = _load_config(config_path)
    default_enabled = default_enabled_slides(config)

    disk = _load_deck_builder_disk_state()

    if not st.session_state.get("_deck_builder_disk_hydrated"):
        st.session_state["_deck_builder_disk_hydrated"] = True
        se = disk.get("slides_enabled")
        if isinstance(se, dict):
            for key in SLIDE_ORDER:
                if key in se:
                    st.session_state[f"inc_{key}"] = bool(se[key])
        sv = disk.get("slide_variants")
        if isinstance(sv, dict):
            for group_key, variant_id in sv.items():
                opts = SLIDE_VARIANT_GROUPS.get(group_key)
                if not opts:
                    continue
                ids = [o["id"] for o in opts]
                if variant_id in ids:
                    st.session_state[f"var_{group_key}"] = ids.index(variant_id)

    if "deck_holdings_text" not in st.session_state:
        sample = PROJECT_ROOT / "data" / "sample_holdings.csv"
        default_path = str(sample) if sample.exists() else ""
        st.session_state.deck_holdings_text = str(disk.get("deck_holdings_text") or default_path)
    if "deck_aum" not in st.session_state:
        st.session_state.deck_aum = str(disk.get("deck_aum") or "€125.4M")
    if "deck_template_label" not in st.session_state:
        st.session_state.deck_template_label = str(
            disk.get("deck_template_label") or "Base config only"
        )

    with st.sidebar:
        st.header("Inputs")
        uploaded = st.file_uploader("Holdings CSV (optional)", type=["csv"])
        holdings_text = st.text_input(
            "Or path to holdings CSV",
            key="deck_holdings_text",
            help="Absolute or project-relative path if you are not uploading a file.",
        )
        report_date = st.date_input("Report date", value=date.today())
        date_str = report_date.strftime("%Y-%m-%d")
        aum = st.text_input("AUM display", key="deck_aum")

        template_label = st.selectbox(
            "Config template",
            options=list(TEMPLATE_CHOICES.keys()),
            key="deck_template_label",
            help="Optional YAML merged on top of fund_config.yaml (see config/templates/).",
        )
        template_path = TEMPLATE_CHOICES[template_label]

        st.divider()
        st.markdown("**Setup:** `pip install -r requirements.txt` then run `streamlit run app_deck_builder.py`")

    st.subheader("1) Include these slides")
    cols = st.columns(4)
    include: dict[str, bool] = {}
    for i, key in enumerate(SLIDE_ORDER):
        label = SLIDE_LABELS.get(key, key.replace("_", " ").title())
        default_on = default_enabled.get(key, False)
        with cols[i % 4]:
            include[key] = st.checkbox(label, value=default_on, key=f"inc_{key}")

    st.subheader("2) Layout style (where options apply)")
    st.caption("Each option changes how that slide looks in the deck — pick what fits your audience.")

    variant_choices: dict[str, str] = {}
    for group_key, options in SLIDE_VARIANT_GROUPS.items():
        if not include.get(group_key, False):
            continue
        labels = [f"**{o['label']}** — {o['description']}" for o in options]
        ids = [o["id"] for o in options]
        default_id = DEFAULT_VARIANTS.get(group_key, ids[0])
        if default_id not in ids:
            default_id = ids[0]
        default_index = ids.index(default_id)
        choice = st.radio(
            SLIDE_LABELS.get(group_key, group_key),
            range(len(options)),
            format_func=lambda i: labels[i],
            index=default_index,
            horizontal=False,
            key=f"var_{group_key}",
        )
        variant_choices[group_key] = ids[int(choice)]

    st.subheader("3) Generate")
    if st.button("Build deck", type="primary"):
        if uploaded is not None:
            holdings_path = PROJECT_ROOT / "output" / "_uploaded_holdings.csv"
            holdings_path.parent.mkdir(parents=True, exist_ok=True)
            holdings_path.write_bytes(uploaded.getvalue())
        else:
            holdings_path = Path(holdings_text.strip())
            if not holdings_path.is_absolute():
                holdings_path = PROJECT_ROOT / holdings_path
            if not holdings_path.is_file():
                st.error(f"Holdings file not found: {holdings_path}")
                st.stop()

        out_dir = PROJECT_ROOT / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_fund = config["fund"]["name"].replace(" ", "_")
        output_path = out_dir / f"{safe_fund}_Report_{date_str}.pptx"
        chart_dir = PROJECT_ROOT / "charts"

        progress = st.progress(0.0, text="Loading data and building deck…")
        pipeline_warnings: list[str] = []
        try:
            generate_deck(
                holdings_path=holdings_path,
                config_path=config_path,
                report_date=date_str,
                aum=aum,
                output_path=output_path,
                chart_dir=chart_dir,
                enabled_slides=include,
                slide_variants=variant_choices,
                template_path=template_path,
                pipeline_warnings=pipeline_warnings,
            )
            progress.progress(1.0, text="Done.")
        except Exception as exc:
            progress.empty()
            st.exception(exc)
            st.stop()

        for msg in pipeline_warnings:
            st.warning(msg)

        _save_deck_builder_disk_state(
            {
                "deck_holdings_text": str(st.session_state.get("deck_holdings_text", "")),
                "deck_aum": str(st.session_state.get("deck_aum", "")),
                "deck_template_label": str(st.session_state.get("deck_template_label", "")),
                "slides_enabled": dict(include),
                "slide_variants": dict(variant_choices),
            }
        )

        st.success(f"Saved: `{output_path}`")
        data = output_path.read_bytes()
        st.download_button(
            label="Download PowerPoint",
            data=data,
            file_name=output_path.name,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )


if __name__ == "__main__":
    main()
