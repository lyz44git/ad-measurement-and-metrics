"""Figures 1 to 6 of the README, drawn from the result files with the panels in figures/figstyle.py.

Usage: python figures/make_figures.py   (writes figures/figure1.png to figure6.png)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403


def figure1():
    """What the ads did in the experiment, and what a simple count credits to them."""
    fig = plt.figure(figsize=(7.4, 3.1), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.15, 0.78], wspace=0.3, left=0.03, right=0.975, top=0.83, bottom=0.12)
    p_rates(fig, gs[0], "A", "Rates by group")
    p_gap(fig, gs[1], "B", "Credited by the count vs. caused")
    p_hundred(fig.add_subplot(gs[2]), "C", title="Of 100 conversions\n      credited by the count")
    save(fig, "figures/figure1.png")


def figure2():
    """Who the ads moved, and segment estimates from a small sample, with and without privacy noise."""
    fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[1.2, 0.8, 1.05]))
    p_deciles(ax[0], "A", "Effect by decile of predicted uplift")
    p_slope(ax[1], "B", "Segment error, ten samples")
    p_privacy(ax[2], "C", "Error under privacy noise")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.2, wspace=0.45)
    save(fig, "figures/figure2.png")


def figure3():
    """Attribution without an experiment: the exposure effect, credit by rule, and bidding."""
    fig, ax = plt.subplots(1, 3, figsize=(7.4, 3.2), dpi=300, gridspec_kw=dict(width_ratios=[0.95, 1.0, 1.05]))
    p_exposure(ax[0], "A", "Effect of exposure on visits")
    p_heat(ax[1], "B", "Credit by rule and touch timing")
    p_bidding(ax[2], "C", "Bidding by rule")
    fig.subplots_adjust(left=0.19, right=0.985, top=0.8, bottom=0.2, wspace=0.62)
    save(fig, "figures/figure3.png")


def figure4():
    """When a marketing mix model can measure a channel."""
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 2.8), dpi=300, gridspec_kw=dict(width_ratios=[1.55, 1]))
    p_mmm_scatter(ax[0], "A", "Recovery error and the signal-to-noise index")
    p_mmm_share(ax[1], "B", "Brand-channels with index ≥ 2")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.17, wspace=0.55)
    save(fig, "figures/figure4.png")


def figure5():
    """Planning the next test."""
    fig, ax = plt.subplots(2, 2, figsize=(7.4, 4.6), dpi=300)
    p_cov_users(ax[0, 0], "A", "Users per arm, one-point lift in visits")
    p_users_lift(ax[0, 1], "B", 0.10, "Users per arm, 10% lift")
    p_geo_grid(ax[1, 0], "C", "adjusted", "Market tests: smallest detectable effect")
    p_forecast_gap(ax[1, 1], "D", "Forecasts across levels")
    fig.subplots_adjust(left=0.17, right=0.95, top=0.92, bottom=0.1, wspace=0.7, hspace=0.62)
    save(fig, "figures/figure5.png")


def figure6():
    """Customer counts and customer models."""
    fig = plt.figure(figsize=(7.4, 3.0), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 0.8, 1.05], wspace=0.95, left=0.02, right=0.96, top=0.84, bottom=0.17)
    p_new_customers(fig.add_subplot(gs[0]), "A", "New under a 3-month look-back")
    p_auc(fig.add_subplot(gs[1]), "B", "Ranking repeat buyers")
    p_rank(fig.add_subplot(gs[2]), "C", "Ranking future sales")
    save(fig, "figures/figure6.png")


if __name__ == "__main__":
    style()
    for f in (figure1, figure2, figure3, figure4, figure5, figure6):
        f()
