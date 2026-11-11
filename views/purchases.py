"""Purchase journal, editing, recurring entries, and CSV interchange."""


import csv
import hashlib
import io

import pandas as pd
import streamlit as st

import data_io as dio
import logic as lg
from ui.common import (
    app_today,
    money,
    page_header,
    refresh_purchase_month_index,
    render_stat_chip,
    whats_next,
)
from ui.undo import capture_state, record_change

NEXT = ("views/swaps_plan.py", "Swaps and plan", "Explore optional alternatives.")
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 5_000


def _csv_row_count(csv_text: str) -> int:
    rows = csv.reader(io.StringIO(csv_text))
    next(rows, None)
    return sum(1 for row in rows if row)


def _restore_preview(
    csv_text: str, mode: str, state, source_signature: str
) -> dict:
    first_id = state.next_id if mode == "Add to current purchases" else 1
    imported, skipped = dio.import_purchases(
        csv_text, first_id=first_id, today=app_today()
    )
    duplicates = 0
    if mode == "Add to current purchases":
        existing = {
            (
                item["date"],
                item["product_type"],
                item["brand"],
                item["condition"],
                item["price_usd"],
            )
            for item in state.purchases
        }
        unique = []
        for item in imported:
            identity = (
                item["date"],
                item["product_type"],
                item["brand"],
                item["condition"],
                item["price_usd"],
            )
            if identity in existing:
                duplicates += 1
                continue
            existing.add(identity)
            unique.append(item)
        imported = [
            {**item, "id": first_id + index}
            for index, item in enumerate(unique)
        ]
    return {
        "signature": source_signature,
        "journal_signature": hashlib.sha256(
            dio.export_purchases(state.purchases).encode("utf-8")
        ).hexdigest(),
        "mode": mode,
        "imported": imported,
        "skipped": skipped,
        "duplicates": duplicates,
    }


@st.dialog("Edit purchase")
def _edit_purchase_dialog(purchase_id: int, rate: float) -> None:
    state = st.session_state
    editing = next(
        (item for item in state.purchases if item["id"] == purchase_id), None
    )
    if editing is None:
        state.editing_id = None
        st.rerun()
    token = state.edit_token
    edit_price = st.number_input(
        f"Price ({lg.CURRENCIES[state.currency_name][0]})",
        min_value=0.0,
        key=f"edit_price_{token}",
    )
    edit_date = st.date_input(
        "Purchase date",
        key=f"edit_date_{token}",
        min_value=lg.MIN_PURCHASE_DATE,
        max_value=lg.max_purchase_date(app_today()),
    )
    edit_brand = st.text_input("Brand or shop", key=f"edit_brand_{token}")
    edit_condition = st.selectbox(
        "Condition",
        list(lg.CONDITION_FACTORS),
        key=f"edit_condition_{token}",
    )
    edit_packaging = st.checkbox(
        "Minimal packaging", key=f"edit_packaging_{token}"
    )
    edit_note = st.text_input(
        "Note (optional)",
        max_chars=lg.MAX_NOTE_LENGTH,
        key=f"edit_note_{token}",
    )
    edit_intent = st.selectbox(
        "Was this a need or a want?",
        ["", *lg.INTENTS],
        format_func=lambda value: value or "Not set",
        key=f"edit_intent_{token}",
    )
    errors = lg.validate_purchase(
        editing["product_type"],
        edit_brand,
        edit_price / rate,
        edit_condition,
        edit_date,
        edit_packaging,
        today=app_today(),
        note=edit_note,
        intent=edit_intent,
    )
    if errors:
        st.error(" ".join(errors))
    save_col, cancel_col = st.columns(2)
    if save_col.button("Save edit", disabled=bool(errors), type="primary"):
        revised = lg.make_purchase(
            editing["id"],
            edit_date,
            editing["product_type"],
            edit_brand,
            edit_price / rate,
            edit_condition,
            edit_packaging,
            today=app_today(),
            note=edit_note,
            intent=edit_intent,
        )
        for field in (
            "recurring",
            "recurring_group",
            "source",
            "swap_from_label",
            "swap_original_co2_kg",
            "swap_original_price_usd",
        ):
            if field in editing:
                revised[field] = editing[field]
        if "swap_original_co2_kg" in revised:
            revised["swap_saved_kg"] = round(
                max(0.0, revised["swap_original_co2_kg"] - revised["co2_kg"]),
                2,
            )
        before = capture_state(state)
        before["purchases"] = [
            dict(item) for item in state.purchases
        ]
        state.purchases = [
            revised if item["id"] == purchase_id else item
            for item in state.purchases
        ]
        refresh_purchase_month_index(state)
        record_change(
            before,
            f"Edited {editing['product_type']} purchase.",
            state,
        )
        state.editing_id = None
        st.rerun()
    if cancel_col.button("Cancel edit", key="cancel_purchase_edit"):
        state.editing_id = None
        st.rerun()


def render() -> None:
    page_header(
        "Purchases",
        "Search, review, edit, and export the entries in your journal.",
        action_label="Explore swaps",
        action_page=NEXT[0],
    )
    state = st.session_state
    purchases = list(state.purchases)
    symbol, rate = lg.CURRENCIES[state.currency_name]
    month = state.view_month
    if purchases:
        month_items = [item for item in purchases if lg.month_of(item["date"]) == month]
        glance = st.columns(3)
        with glance[0]:
            render_stat_chip("Journal entries", str(len(purchases)), [len(purchases)])
        with glance[1]:
            render_stat_chip("This month", str(len(month_items)), [len(month_items)])
        with glance[2]:
            render_stat_chip(
                "Categories explored",
                str(len({item["product_type"] for item in purchases})),
                [len({item["product_type"] for item in purchases})],
            )
    st.markdown("## Purchase history")
    st.caption("Your full journal across all months. Use search and filters to focus the view.")
    if not purchases:
        st.markdown(
            '<div class="studio-empty"><span class="section-label">A PLACE FOR EVERY CHOICE</span>'
            '<h3>Your journal is ready.</h3><p>Add purchases as you go, revisit details '
            'when you need to, and keep a portable copy with CSV export.</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link("views/home.py", label="Add a purchase →")
        if st.button("Try with demo data", key="purchases_load_demo"):
            from ui.actions import load_demo

            load_demo()
            st.rerun()
    else:
        filter_cols = st.columns([1.5, 1, 1, 1, 1.1])
        query = filter_cols[0].text_input("Search", key="purchase_search")
        categories = ["All categories", *lg.PRODUCTS]
        category = filter_cols[1].selectbox(
            "Category", categories, key="purchase_filter_category"
        )
        condition_options = ["All conditions", *lg.CONDITION_FACTORS]
        condition = filter_cols[2].selectbox(
            "Condition", condition_options, key="purchase_filter_condition"
        )
        intent_options = ["All intents", "Not set", *lg.INTENTS]
        intent_filter = filter_cols[3].selectbox(
            "Intent", intent_options, key="purchase_filter_intent"
        )
        sort_order = filter_cols[4].selectbox(
            "Sort", ["Newest first", "Oldest first", "Highest estimate", "Lowest estimate"],
            key="purchase_sort",
        )
        filtered = [
            item
            for item in purchases
            if (category == "All categories" or item["product_type"] == category)
            and (condition == "All conditions" or item["condition"] == condition)
            and (
                intent_filter == "All intents"
                or (
                    intent_filter == "Not set"
                    and not item.get("intent")
                )
                or item.get("intent") == intent_filter
            )
            and query.casefold() in (
                f"{item['product_type']} {item['brand']} {item['condition']} "
                f"{item.get('note', '')}".casefold()
            )
        ]
        key_fn = {
            "Newest first": lambda item: item["date"],
            "Oldest first": lambda item: item["date"],
            "Highest estimate": lambda item: item["co2_kg"],
            "Lowest estimate": lambda item: item["co2_kg"],
        }[sort_order]
        filtered.sort(
            key=key_fn,
            reverse=sort_order in {"Newest first", "Highest estimate"},
        )
        if filtered:
            page_size = 25
            page_count = max(1, (len(filtered) + page_size - 1) // page_size)
            page_number = min(max(int(state.get("purchase_page", 1)), 1), page_count)
            state.purchase_page = page_number
            totals = lg.monthly_summary(filtered, month)
            st.caption(
                f"Showing {len(filtered)} of {len(purchases)} entries · "
                f"{money(totals['spend_usd'], rate, symbol)} selected-month spend · "
                f"{totals['co2_kg']:.1f} kg CO₂e estimated"
            )
            page_start = (page_number - 1) * page_size
            page_items = filtered[page_start : page_start + page_size]
            table = [
                {
                    "Date": item["date"].strftime("%d %b %Y"),
                    "Product": item["product_type"],
                    "Brand": item["brand"],
                    "Condition": item["condition"],
                    "Intent": item.get("intent") or "—",
                    "Price": money(item["price_usd"], rate, symbol),
                    "CO₂e (kg)": item["co2_kg"],
                    "Impact": item["rating"],
                    "Entry": (
                        "Synthetic demo"
                        if item.get("source") == "demo"
                        else "Swap"
                        if item.get("source") == "swap"
                        else "Recurring"
                        if item.get("recurring")
                        else "Purchase"
                    ),
                }
                for item in page_items
            ]
            table_key = (
                "purchase_history_"
                f"{page_number}_"
                + "_".join(str(item["id"]) for item in page_items)
            )
            selection = st.dataframe(
                pd.DataFrame(table),
                hide_index=True,
                width="stretch",
                on_select="rerun",
                selection_mode="multi-row",
                key=table_key,
                alt="Purchase history. Select one row to edit, or rows to delete.",
            )
            selected_rows = selection.selection.rows
            selected_items = [
                page_items[row_index]
                for row_index in selected_rows
                if 0 <= row_index < len(page_items)
            ]
            if selected_items:
                state.selected_purchase_action_id = selected_items[0]["id"]
            if state.get("selected_purchase_action_id") not in {
                item["id"] for item in page_items
            }:
                state.selected_purchase_action_id = None
            st.caption(
                "Select a table row with the mouse or keyboard. Select one row to edit; "
                "select one or more rows to delete. The keyboard-accessible selector "
                "below is an alternative."
            )
            st.selectbox(
                "Selected purchase",
                [None, *[item["id"] for item in page_items]],
                format_func=lambda purchase_id: (
                    "Choose a purchase"
                    if purchase_id is None
                    else next(
                        f"{item['date']:%d %b %Y} · {item['product_type']} · "
                        f"{item['brand']}"
                        for item in page_items
                        if item["id"] == purchase_id
                    )
                ),
                key="selected_purchase_action_id",
            )
            selected_ids = (
                {item["id"] for item in selected_items}
                if selected_items
                else (
                    {state.selected_purchase_action_id}
                    if state.selected_purchase_action_id is not None
                    else set()
                )
            )
            edit_col, delete_col = st.columns(2)
            if edit_col.button(
                "Edit selected",
                disabled=len(selected_ids) != 1,
                key="edit_selected_purchase",
            ):
                selected_id = next(iter(selected_ids))
                item = next(item for item in page_items if item["id"] == selected_id)
                token = state.get("edit_token", 0) + 1
                state.edit_token = token
                state.editing_id = item["id"]
                state[f"edit_price_{token}"] = item["price_usd"] * rate
                state[f"edit_date_{token}"] = item["date"]
                state[f"edit_brand_{token}"] = item["brand"]
                state[f"edit_condition_{token}"] = item["condition"]
                state[f"edit_packaging_{token}"] = item["low_packaging"]
                state[f"edit_note_{token}"] = item.get("note", "")
                state[f"edit_intent_{token}"] = item.get("intent", "")
                st.rerun()
            if delete_col.button(
                "Delete selected",
                disabled=not selected_ids,
                key="bulk_delete",
            ):
                before = capture_state(state)
                deleted_count = sum(item["id"] in selected_ids for item in purchases)
                state.purchases = [
                    item for item in purchases if item["id"] not in selected_ids
                ]
                refresh_purchase_month_index(state)
                description = (
                    "Deleted 1 purchase."
                    if deleted_count == 1
                    else f"Deleted {deleted_count} purchases."
                )
                record_change(before, description, state)
                st.rerun()
            if page_count > 1:
                previous_col, page_label_col, next_col = st.columns([1, 2, 1])
                if previous_col.button(
                    "Previous", disabled=page_number == 1, key="purchases_previous_page"
                ):
                    state.purchase_page = page_number - 1
                    st.rerun()
                page_label_col.caption(
                    f"Page {page_number} of {page_count} · {page_size} rows per page"
                )
                if next_col.button(
                    "Next", disabled=page_number == page_count, key="purchases_next_page"
                ):
                    state.purchase_page = page_number + 1
                    st.rerun()
        else:
            st.markdown(
                '<div class="studio-empty"><h3>No matches in this view.</h3>'
                '<p>Try a shorter search or choose All categories, All conditions '
                'and All intents to broaden the results.</p></div>',
                unsafe_allow_html=True,
            )

    if state.get("editing_id") is not None:
        _edit_purchase_dialog(state.editing_id, rate)

    with st.expander("Recurring purchase series"):
        series = {
            item.get("recurring_group"): item
            for item in state.purchases
            if item.get("recurring") and item.get("recurring_group")
        }
        if series:
            chosen = st.selectbox(
                "Series to remove",
                list(series),
                format_func=lambda group: (
                    f"{series[group]['product_type']} · {series[group]['brand']}"
                ),
            )
            if st.button("Remove selected series"):
                before = capture_state(state)
                removed_count = sum(
                    item.get("recurring_group") == chosen
                    for item in state.purchases
                )
                state.purchases = [
                    item
                    for item in state.purchases
                    if item.get("recurring_group") != chosen
                ]
                refresh_purchase_month_index(state)
                record_change(
                    before,
                    f"Removed recurring series ({removed_count} purchases).",
                    state,
                )
                st.rerun()
        else:
            st.caption("Monthly repeats will appear here.")

    with st.expander("Quick-add manager"):
        favorites = state.get("favorites", [])
        if favorites:
            for index, favorite in enumerate(favorites):
                st.write(
                    f"{favorite['product_type']} · {favorite['brand']} · "
                    f"{favorite['condition']} · {favorite['price_usd']:.2f} USD"
                )
                if st.button("Remove", key=f"remove_favorite_{index}"):
                    state.favorites = [
                        item for item in favorites if item != favorite
                    ]
                    st.rerun()
        else:
            st.caption("Save a purchase as a quick add from Home.")

    st.markdown("## CSV interchange")
    st.caption("Keep a portable copy of your journal, or preview a CSV before restoring it.")
    st.download_button(
        "Download all purchases as CSV",
        dio.export_purchases(state.purchases),
        "shopimpact_purchases.csv",
        "text/csv",
        disabled=not state.purchases,
    )
    upload = st.file_uploader(
        "Restore from CSV",
        type=["csv"],
        key=f"restore_csv_{state.get('restore_upload_revision', 0)}",
        help="CO₂e estimates are recalculated on import.",
    )
    import_mode = st.radio(
        "When restoring",
        ["Replace current purchases", "Add to current purchases"],
        horizontal=True,
        key="import_mode",
    )
    upload_bytes = upload.getvalue() if upload is not None else None
    upload_is_too_large = upload_bytes is not None and len(upload_bytes) > MAX_CSV_BYTES
    if upload_is_too_large:
        state.csv_restore_error = "file_size"
        st.error("This CSV is larger than 2 MB. Choose a smaller file to restore.")
    elif upload_bytes is not None:
        state.csv_restore_error = None

    if st.button(
        "Preview restore",
        disabled=upload_bytes is None or upload_is_too_large,
        key="preview_csv_restore",
    ) and upload_bytes is not None:
        try:
            csv_text = upload_bytes.decode("utf-8-sig")
            row_count = _csv_row_count(csv_text)
            if row_count > MAX_CSV_ROWS:
                state.restore_preview = None
                state.csv_restore_error = "row_limit"
                st.error(
                    f"This CSV has {row_count:,} rows; the limit is "
                    f"{MAX_CSV_ROWS:,}. Choose a smaller file."
                )
            else:
                state.restore_preview = _restore_preview(
                    csv_text,
                    import_mode,
                    state,
                    hashlib.sha256(upload_bytes).hexdigest(),
                )
                state.csv_restore_error = None
                state.restore_preview_token = state.get("restore_preview_token", 0) + 1
        except (UnicodeDecodeError, ValueError, csv.Error) as error:
            state.restore_preview = None
            state.csv_restore_error = "invalid_csv"
            st.error(f"CSV could not be previewed: {error}")
    preview = state.get("restore_preview")
    current_signature = (
        hashlib.sha256(upload_bytes).hexdigest()
        if upload_bytes is not None and not upload_is_too_large
        else None
    )
    if preview and (
        current_signature != preview["signature"]
        or import_mode != preview["mode"]
        or hashlib.sha256(
            dio.export_purchases(state.purchases).encode("utf-8")
        ).hexdigest()
        != preview["journal_signature"]
    ):
        preview = None
        st.info(
            "The file, restore mode, or journal changed. Preview the CSV again to continue."
        )

    if preview:
        imported = preview["imported"]
        skipped = preview["skipped"]
        st.markdown("### Restore preview")
        st.write(
            f"**{len(imported)} row(s) will be imported** · "
            f"**{len(skipped)} row(s) will be skipped**"
        )
        if imported:
            dates = [item["date"] for item in imported]
            st.caption(
                f"Date range: {min(dates):%d %b %Y} – {max(dates):%d %b %Y} · "
                f"Total: {sum(item['co2_kg'] for item in imported):.1f} kg CO₂e"
            )
        if preview["duplicates"]:
            st.info(
                f"{preview['duplicates']} duplicate purchase(s) will be skipped."
            )
        if skipped:
            with st.expander("Rows skipped and reasons"):
                for row, reason in skipped:
                    st.warning(f"CSV row {row}: {reason}")
        if not imported:
            st.error("No valid, non-duplicate purchases can be imported. Your journal is unchanged.")
        elif import_mode == "Replace current purchases":
            removal_count = len(state.purchases)
            st.warning(
                f"Replace will remove {removal_count} current purchase(s) and "
                f"add {len(imported)} imported purchase(s)."
            )
            confirmed = st.checkbox(
                f"I understand Replace will remove {removal_count} current purchases.",
                key=f"confirm_csv_replace_{state.restore_preview_token}",
            )
            apply_label = "Confirm Replace"
        else:
            confirmed = True
            noun = "purchase" if len(imported) == 1 else "purchases"
            apply_label = f"Add {len(imported)} {noun}"
        if imported and st.button(
            apply_label,
            disabled=not confirmed,
            key="apply_csv_restore",
        ):
            before = capture_state(state)
            if import_mode == "Replace current purchases":
                state.purchases = imported
            else:
                state.purchases.extend(imported)
            state.next_id = max(
                (item["id"] for item in state.purchases), default=0
            ) + 1
            refresh_purchase_month_index(state)
            state.import_report = {
                "imported": len(imported),
                "skipped": skipped,
                "duplicates": preview["duplicates"],
            }
            mode_description = "Replaced the journal from CSV."
            if import_mode == "Add to current purchases":
                noun = "purchase" if len(imported) == 1 else "purchases"
                mode_description = f"Added {len(imported)} {noun} from CSV."
            record_change(before, mode_description, state)
            state.restore_preview = None
            st.rerun()

    report = state.get("import_report")
    if report:
        if report["imported"]:
            st.success(f"Restored {report['imported']} purchase(s).")
        if report.get("duplicates"):
            st.info(f"Skipped {report['duplicates']} duplicate purchase(s).")
        for row, reason in report["skipped"]:
            st.warning(f"Skipped CSV row {row}: {reason}")

    if state.get("csv_restore_error"):
        st.info("That CSV could not be restored; your current journal is unchanged.")
        if st.button("Choose a different CSV", key="retry_csv_restore"):
            state.csv_restore_error = None
            state.restore_upload_revision = state.get("restore_upload_revision", 0) + 1
            st.rerun()

    st.markdown("## Saved-data status")
    if state.storage_error:
        st.warning(state.storage_error)
    elif state.storage_available:
        st.caption(f"Saved in this browser · {len(state.purchases)} purchase(s).")
    else:
        st.info("Browser storage is unavailable; the current session remains usable.")
    whats_next(*NEXT)


render()
