from __future__ import annotations

from flask import Blueprint, render_template

from app.services.common import today

pages = Blueprint("pages", __name__)


@pages.get("/")
def overview_page():
    return render_template("overview.html", active_page="overview", today=today().isoformat())


@pages.get("/transactions")
def transactions_page():
    return render_template("transactions.html", active_page="transactions", today=today().isoformat())


@pages.get("/budget")
def budget_page():
    return render_template(
        "budget.html",
        active_page="budget",
        current_month=today().strftime("%Y-%m"),
    )

