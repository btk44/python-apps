-- ============================================================
-- SEED DATA: CURRENCIES
-- ISO 4217 currency codes with correct decimal precision.
-- decimals: most currencies use 2, some (e.g. JPY, KRW) use 0,
-- and a few (e.g. KWD, BHD, OMR) use 3.
-- Safe to re-run: ON CONFLICT (code) DO NOTHING skips duplicates.
-- ============================================================

INSERT INTO currencies (code, name, symbol, decimals) VALUES
    ('USD', 'US Dollar',            '$',   2),
    ('EUR', 'Euro',                 '€',   2),
    ('GBP', 'British Pound',        '£',   2),
    ('PLN', 'Polish Zloty',         'zł',  2),
    ('CHF', 'Swiss Franc',          'CHF', 2),
    ('CAD', 'Canadian Dollar',      '$',   2),
    ('AUD', 'Australian Dollar',    '$',   2),
    ('NZD', 'New Zealand Dollar',   '$',   2),
    ('SEK', 'Swedish Krona',        'kr',  2),
    ('NOK', 'Norwegian Krone',      'kr',  2),
    ('DKK', 'Danish Krone',         'kr',  2),
    ('CZK', 'Czech Koruna',         'Kč',  2),
    ('HUF', 'Hungarian Forint',     'Ft',  2),
    ('RON', 'Romanian Leu',         'lei', 2),
    ('JPY', 'Japanese Yen',         '¥',   0),
    ('KRW', 'South Korean Won',     '₩',   0),
    ('CNY', 'Chinese Yuan',         '¥',   2),
    ('HKD', 'Hong Kong Dollar',     '$',   2),
    ('SGD', 'Singapore Dollar',     '$',   2),
    ('INR', 'Indian Rupee',         '₹',   2),
    ('BRL', 'Brazilian Real',       'R$',  2),
    ('MXN', 'Mexican Peso',         '$',   2),
    ('ZAR', 'South African Rand',   'R',   2),
    ('TRY', 'Turkish Lira',         '₺',   2),
    ('AED', 'UAE Dirham',           'د.إ', 2),
    ('SAR', 'Saudi Riyal',          '﷼',   2),
    ('ILS', 'Israeli New Shekel',   '₪',   2),
    ('KWD', 'Kuwaiti Dinar',        'د.ك', 3),
    ('BHD', 'Bahraini Dinar',       '.د.ب',3),
    ('OMR', 'Omani Rial',           '﷼',   3)
ON CONFLICT (code) DO NOTHING;