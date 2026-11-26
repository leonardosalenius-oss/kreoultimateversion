import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from kreo_admin_rimanenze import closing_dates, inventory_closings, stock_change


def product(key="A", standard=0, updated="2024-01-01"):
    return dict(prodotto_id=key, costo_standard=standard, updated_at=updated)


def entry(key, day, quantity, cost=None, *, sku="A", kind="acquisto", source=None, status="valido"):
    return dict(movimento_id=key, prodotto_id=sku, data_movimento=day, tipo=kind,
                quantita=quantity, costo_unitario=cost, stato=status, movimento_origine_id=source)


class InventoryClosingsTest(unittest.TestCase):
    def test_partial_months_leap_day_and_empty_month(self):
        dates = closing_dates(date(2024, 1, 20), date(2024, 3, 5))
        self.assertEqual(dates, [date(2024, 1, 19), date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 5)])
        entries = [entry(1, "2024-01-19", 3, 2), entry(2, "2024-01-20", -1, kind="vendita"),
                   entry(3, "2024-03-05", 1, 10), entry(4, "2024-03-06", 10, 100)]
        values = list(inventory_closings([product()], entries[::-1], dates).values())
        self.assertEqual(values, [6, 4, 4, 12])
        self.assertEqual(sum(stock_change(a, b) for a, b in zip(values, values[1:])), 6)
        self.assertEqual(closing_dates(date(2025, 1, 1), date(2025, 1, 1)),
                         [date(2024, 12, 31), date(2025, 1, 1)])

    def test_zero_cost_weighting_and_database_rounding(self):
        dates = [date(2024, 1, 2), date(2024, 1, 3)]
        entries = [entry(1, "2024-01-02", 1, 0), entry(2, "2024-01-03", 2, 1),
                   entry(3, "2024-01-03", 147, kind="rettifica_positiva")]
        values = inventory_closings([product(standard=99)], entries, dates)
        self.assertEqual(list(values.values()), [0, Decimal("100.01")])
        values = inventory_closings([product(), product("B")],
                                   [entry(1, "2024-01-02", 1, "0.005"), entry(2, "2024-01-02", 1, "0.005", sku="B")], dates)
        self.assertEqual(values[dates[0]], Decimal("0.01"))

    def test_only_a_documented_standard_can_value_an_unpriced_adjustment(self):
        dates = [date(2024, 1, 2), date(2024, 1, 3)]
        entries = [entry(1, "2024-01-02", 2, kind="rettifica_positiva")]
        updated = "2024-01-02T23:35:00+00:00"  # In Italia è il 3 gennaio.
        self.assertEqual(list(inventory_closings([product(standard=4, updated=updated)], entries, dates).values()), [None, 8])
        self.assertIsNone(stock_change(None, Decimal(8)))
        self.assertEqual(list(inventory_closings([product(standard=0)], entries, dates).values()), [0, 0])

    def test_dated_reversals_of_purchase_and_sale(self):
        dates = [date(2024, 1, day) for day in range(1, 6)]
        entries = [entry(1, "2024-01-01", 2, 10), entry(2, "2024-01-02", 2, 20, status="annullato"),
                   entry(3, "2024-01-03", -1, 0, kind="vendita", status="annullato"),
                   entry(4, "2024-01-04", -2, 20, kind="storno", source=2),
                   entry(5, "2024-01-05", 1, 0, kind="storno", source=3),
                   entry(6, "2024-01-01", 2, 90, status="annullato")]
        self.assertEqual(list(inventory_closings([product()], entries, dates).values()), [20, 60, 45, 10, 20])

    def test_admin_revenues_result_and_monthly_rows_share_the_same_boundaries(self):
        import db
        with patch.object(db, "get_db", return_value=None), patch.object(db, "get_auth_client", return_value=None):
            import app
        products = [dict(product(), giacenza=100, costo_medio=10)]
        entries = [entry(1, "2024-01-19", 2, 3), entry(2, "2024-01-20", -1, kind="vendita"),
                   entry(3, "2024-03-04", 3, 5)]
        receipts = [dict(data_incasso="2024-01-20", tipo_incasso=kind, importo=value)
                    for kind, value in [("abbonamento", 100), ("giacenze_magazzino", 750),
                                        ("vendita_prodotto", 15), ("altro_ricavo", 7)]]
        subs = [dict(data_inizio="2024-01-20", prezzo_concordato=100)]
        costs = [dict(competenza_mese="2024-03-01", totale=80)]
        loaders = dict(load_clients=lambda: [], load_prospects=lambda: [], load_subscriptions=lambda: subs,
                       load_receipts=lambda: receipts, load_expenses=lambda: costs, load_installments=lambda: [],
                       load_inventory_products=lambda: products, load_inventory_movements=lambda: entries,
                       load_admin_inventory_history=lambda: (products, entries), presenze_disponibili=lambda *_: None)
        with patch.multiple(app, **loaders):
            snap = app.build_admin_snapshot(date(2024, 1, 20), date(2024, 3, 5))
        self.assertEqual((snap["income_total"], snap["expenses_total"], snap["inventory_change"],
                          snap["operating_result"], snap["inventory_value"]), (122, 80, 10.8, 52.8, 1000))
        self.assertEqual([r["variazione_rimanenze"] for r in snap["monthly_rows"]], [-3, 0, 13.8])
        self.assertEqual([r["risultato"] for r in snap["monthly_rows"]], [119, 0, -66.2])


if __name__ == "__main__":
    unittest.main()
