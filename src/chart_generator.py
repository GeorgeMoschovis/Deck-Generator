"""
chart_generator.py
------------------
Generates matplotlib charts as PNG images for embedding into slides.
"""

import matplotlib

matplotlib.use("Agg")
from typing import Any, Mapping

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

DEFAULT_PALETTE: dict[str, str] = {
    "primary": "tab:blue",
    "secondary": "tab:cyan",
    "accent": "tab:orange",
    "positive": "tab:green",
    "negative": "tab:red",
    "muted": "tab:gray",
    "bg": "white",
    "grid": "lightgray",
}


def _normalize_colour(value: Any) -> str | None:
    """Normalize YAML color values to matplotlib-friendly strings."""
    if not isinstance(value, str):
        return None

    colour = value.strip()
    if not colour:
        return None

    # Branding config stores hex as bare 6-char strings.
    is_hex_triplet = len(colour) == 6 and all(c in "0123456789abcdefABCDEF" for c in colour)
    if is_hex_triplet:
        return f"#{colour}"

    return colour


def _build_palette(
    branding: Mapping[str, Any] | None = None,
    palette_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build chart palette from config branding with safe defaults."""
    branding = branding or {}

    resolved = {
        "primary": _normalize_colour(branding.get("primary_color")),
        "secondary": _normalize_colour(branding.get("secondary_color")),
        "accent": _normalize_colour(branding.get("accent_color")),
        "positive": _normalize_colour(branding.get("positive_color")),
        "negative": _normalize_colour(branding.get("negative_color")),
        "muted": _normalize_colour(branding.get("text_muted")),
        "bg": _normalize_colour(branding.get("bg_light")),
        "grid": _normalize_colour(branding.get("grid_color")),
    }

    palette = DEFAULT_PALETTE.copy()
    for key, value in resolved.items():
        if value is not None:
            palette[key] = value

    if palette_overrides:
        for key, value in palette_overrides.items():
            normalized_value = _normalize_colour(value)
            if normalized_value is not None:
                resolved_key = key.lower()
                if resolved_key in DEFAULT_PALETTE:
                    palette[resolved_key] = normalized_value

    return palette


def _apply_style(ax, palette: Mapping[str, str], title: str = "") -> None:
    ax.set_facecolor(palette["bg"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(palette["grid"])
    ax.spines["bottom"].set_color(palette["grid"])
    ax.tick_params(colors=palette["muted"], labelsize=9)
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=palette["primary"], pad=12)


def cumulative_return_chart(
    returns: pd.Series,
    output_path: str,
    benchmark_returns: pd.Series | None = None,
    branding: Mapping[str, Any] | None = None,
    palette_overrides: Mapping[str, str] | None = None,
) -> None:
    """Line chart of cumulative returns."""
    palette = _build_palette(branding, palette_overrides)
    fig, ax = plt.subplots(figsize=(8, 3.5), dpi=200)
    cum = (1 + returns).cumprod() - 1
    ax.plot(cum.index, cum.values * 100, color=palette["primary"], linewidth=2, label="Portfolio")
    if benchmark_returns is not None and not benchmark_returns.empty:
        bm_aligned = benchmark_returns.reindex(returns.index).ffill().bfill().fillna(0.0)
        bm_cum = (1 + bm_aligned).cumprod() - 1
        ax.plot(
            bm_cum.index,
            bm_cum.values * 100,
            color=palette["muted"],
            linewidth=1.5,
            linestyle="--",
            label="Benchmark",
        )
        ax.legend(fontsize=8, frameon=False)
    ax.fill_between(cum.index, 0, cum.values * 100, alpha=0.08, color=palette["primary"])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    _apply_style(ax, palette, "Cumulative Performance")
    ax.axhline(0, color=palette["grid"], linewidth=0.8, zorder=0)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", facecolor=palette["bg"])
    plt.close(fig)


def drawdown_chart(
    returns: pd.Series,
    output_path: str,
    branding: Mapping[str, Any] | None = None,
    palette_overrides: Mapping[str, str] | None = None,
) -> None:
    """Drawdown chart."""
    palette = _build_palette(branding, palette_overrides)
    cumulative = (1 + returns).cumprod()
    drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax() * 100
    fig, ax = plt.subplots(figsize=(8, 2.5), dpi=200)
    ax.fill_between(drawdown.index, drawdown.values, 0, color=palette["negative"], alpha=0.3)
    ax.plot(drawdown.index, drawdown.values, color=palette["negative"], linewidth=1)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    _apply_style(ax, palette, "Drawdown")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", facecolor=palette["bg"])
    plt.close(fig)


def bar_chart(
    data: pd.Series,
    output_path: str,
    title: str = "",
    horizontal: bool = False,
    branding: Mapping[str, Any] | None = None,
    palette_overrides: Mapping[str, str] | None = None,
) -> None:
    """Bar chart for exposure breakdowns."""
    palette = _build_palette(branding, palette_overrides)
    fig, ax = plt.subplots(figsize=(8, 3.5), dpi=200)
    colours = [palette["primary"] if v >= 0 else palette["negative"] for v in data.values]
    if horizontal:
        ax.barh(data.index, data.values, color=colours, height=0.6)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    else:
        ax.bar(data.index, data.values, color=colours, width=0.6)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
        plt.xticks(rotation=45, ha="right", fontsize=8)
    _apply_style(ax, palette, title)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", facecolor=palette["bg"])
    plt.close(fig)


def pie_chart(
    data: pd.Series,
    output_path: str,
    title: str = "",
    branding: Mapping[str, Any] | None = None,
    palette_overrides: Mapping[str, str] | None = None,
) -> None:
    """Pie chart for allocation breakdowns."""
    palette = _build_palette(branding, palette_overrides)
    fig, ax = plt.subplots(figsize=(5, 5), dpi=200)
    base_colours = [
        palette["primary"],
        palette["secondary"],
        palette["accent"],
        palette["muted"],
        palette["positive"],
        palette["negative"],
    ]
    colours = [base_colours[i % len(base_colours)] for i in range(len(data))]
    pie_out = ax.pie(
        data.values,
        labels=data.index,
        autopct="%.1f%%",
        colors=colours,
        startangle=90,
        pctdistance=0.75,
        textprops={"fontsize": 9},
    )
    autotexts = pie_out[2] if len(pie_out) > 2 else ()
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color(palette["primary"])
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=palette["primary"], pad=16)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", facecolor=palette["bg"])
    plt.close(fig)
