#!/usr/bin/env python3
"""
Test script for grocery parser - validates quantity and unit recognition
in both Dutch and English inputs.
"""

from app.utils.grocery_parser import parse_grocery_input


def test_parser():
    """Test various input formats for the grocery parser."""
    test_cases = [
        # Format: (input, expected_quantity, expected_unit, expected_product)
        # Dutch inputs with quantities (normalized units)
        ("2 kg tomaten", "2", "kg", "tomaten"),
        ("500 gram kaas", "500", "g", "kaas"),  # gram → g
        ("1 kilo appels", "1", "kg", "appels"),  # kilo → kg
        ("3 stuks brood", "3", "stuks", "brood"),
        ("250 ons gehakt", "250", "ons", "gehakt"),
        ("1 liter melk", "1", "liter", "melk"),
        ("2 flessen wijn", "2", "fles", "wijn"),  # flessen → fles (singular)
        ("3 blikken tomaten", "3", "blik", "tomaten"),  # blikken → blik
        ("1 pak suiker", "1", "pak", "suiker"),
        ("2 zakken chips", "2", "zak", "chips"),  # zakken → zak
        # English inputs with quantities (translated to Dutch units)
        ("2 lb chicken", "2", "lb", "chicken"),
        ("500 g cheese", "500", "g", "cheese"),
        ("3 pieces bread", "3", "stuks", "bread"),  # pieces → stuks
        ("1 bottle wine", "1", "fles", "wine"),  # bottle → fles
        ("2 cans tomatoes", "2", "blik", "tomatoes"),  # cans → blik
        ("1 bag sugar", "1", "zak", "sugar"),  # bag → zak
        # Decimal quantities (comma normalized to dot)
        ("2.5 kg vlees", "2.5", "kg", "vlees"),
        ("1,5 liter melk", "1.5", "liter", "melk"),  # 1,5 → 1.5
        ("0.5 kg kaas", "0.5", "kg", "kaas"),
        # Range quantities
        ("2-3 kg aardappelen", "2-3", "kg", "aardappelen"),
        ("1-2 stuks bloemkool", "1-2", "stuks", "bloemkool"),
        # No quantities (just product names)
        ("brood", None, None, "brood"),
        ("melk", None, None, "melk"),
        ("kaas", None, None, "kaas"),
        ("Tomaten", None, None, "tomaten"),
        # Edge cases
        ("2kg tomaten", "2", "kg", "tomaten"),  # No space between quantity and unit
        ("500g kaas", "500", "g", "kaas"),
        ("Verse basilicum", None, None, "verse basilicum"),
        ("Extra vergine olijfolie", None, None, "extra vergine olijfolie"),
    ]

    print("Testing Grocery Parser")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, (input_text, exp_qty, exp_unit, exp_product) in enumerate(test_cases, 1):
        qty, unit, product = parse_grocery_input(input_text)

        # Normalize for comparison
        success = qty == exp_qty and unit == exp_unit and product == exp_product

        status = "✓ PASS" if success else "✗ FAIL"

        print(f"\n{i:2d}. {status} | Input: '{input_text}'")
        print(f"    Expected: qty={exp_qty}, unit={exp_unit}, product='{exp_product}'")
        print(f"    Got:      qty={qty}, unit={unit}, product='{product}'")

        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    import sys

    success = test_parser()
    sys.exit(0 if success else 1)
