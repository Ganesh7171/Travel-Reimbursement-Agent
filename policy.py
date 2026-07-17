# policy.py
from datetime import date

# --- Per-diem limits (USD) ---
PER_DIEM_LIMITS = {
    'meals':            {'daily_limit': 75.0,  'policy': 'POL-PD-01'},
    'lodging':          {'daily_limit': 200.0, 'policy': 'POL-PD-02'},
    'ground_transport': {'daily_limit': 50.0,  'policy': 'POL-PD-03'},
}

# --- Ineligible categories (POL-CAT-02) ---
INELIGIBLE_CATEGORIES = {
    'spa', 'gym', 'minibar', 'alcohol', 'entertainment',
    'personal_shopping', 'gifts', 'traffic_fine', 'personal',
    'in_room_movie', 'penalty', 'late_fee',
}

# --- Eligible categories (POL-CAT-01) ---
ELIGIBLE_CATEGORIES = {
    'airfare', 'lodging', 'meals', 'ground_transport',
    'conference_fees', 'registration_fees', 'taxi', 'rideshare',
    'train', 'rental_car', 'parking',
}

# --- Approval thresholds ---
APPROVAL_THRESHOLDS = [
    {'max': 500,          'tier': 'AUTO',     'policy': 'POL-APR-01', 'decision_eligible': True},
    {'max': 2000,         'tier': 'MANAGER',  'policy': 'POL-APR-02', 'decision_eligible': True},
    {'max': float('inf'), 'tier': 'DIRECTOR', 'policy': 'POL-APR-03', 'decision_eligible': False},
]

# --- Policy rule text for lookup ---
POLICY_RULES = {
    'POL-CAT-01': 'Eligible categories: Airfare (economy class only), Lodging (hotel room charges), Meals (subject to per-diem limits), Ground transport (taxi, rideshare, train, rental car, parking), Conference/registration fees.',
    'POL-CAT-02': 'Ineligible items (never reimbursable): Alcohol and minibar charges, Spa/gym/personal entertainment, In-room movies, personal shopping, gifts, Traffic fines/penalties/late fees, Any personal (non-business) expense.',
    'POL-PD-01':  'Meals: Maximum $75 per day. Amounts above the daily cap are deducted; the rest is reimbursed.',
    'POL-PD-02':  'Lodging: Maximum $200 per night. Amounts above the nightly cap are deducted; the rest is reimbursed.',
    'POL-PD-03':  'Ground transport: Maximum $50 per day. Amounts above the cap are deducted.',
    'POL-AIR-01': 'Airfare class: Only economy class is reimbursable. Business/first-class fares are a policy exception and must be routed to Manual Review (pre-approval may exist).',
    'POL-RCT-01': 'Receipt required above $25: Any single line item > $25 requires an attached, itemized receipt. Airfare and lodging ALWAYS require a receipt regardless of amount.',
    'POL-RCT-02': 'Missing receipt handling: If a receipt is missing for an item that requires one, the claim is routed to Manual Review so the reviewer can request the receipt.',
    'POL-APR-01': 'Auto-approve tier: Total reimbursable <= $500 may be auto-approved if fully compliant.',
    'POL-APR-02': 'Manager tier: Total > $500 and <= $2,000 is eligible for approval when fully compliant.',
    'POL-APR-03': 'Director/Manual-Review tier: Total > $2,000 must be routed to Manual Review (director approval required).',
    'POL-TIME-01': 'Submission window: Claims must be submitted within 30 days of the expense date. Late claims are routed to Manual Review.',
}

SUBMISSION_WINDOW_DAYS = 30

# --- Sample Claims (Appendix B) ---
CLAIMS = [
    {
        'claim_id': 'CLM-001',
        'purpose': 'Attend 2-day industry conference (business)',
        'employee': 'A. Rivera',
        'trip_start': '2026-06-10', 'trip_end': '2026-06-12',
        'submission_date': '2026-06-20',
        'trip_days': 3,
        'total_claimed': 1110.00,
        'line_items': [
            {'category': 'airfare',         'description': 'Round-trip economy airfare', 'amount': 420.00, 'receipt_attached': True,  'is_business_class': False},
            {'category': 'lodging',         'description': 'Hotel, 2 nights @ $180',    'amount': 360.00, 'receipt_attached': True,  'days': 2},
            {'category': 'meals',           'description': 'Meals, 3 days @ ~$60/day',  'amount': 180.00, 'receipt_attached': True,  'days': 3},
            {'category': 'conference_fees', 'description': 'Conference registration',   'amount': 150.00, 'receipt_attached': True},
        ]
    },
    {
        'claim_id': 'CLM-002',
        'purpose': 'Weekend hotel stay',
        'employee': 'B. Osei',
        'trip_start': '2026-06-14', 'trip_end': '2026-06-15',
        'submission_date': '2026-06-25',
        'trip_days': 2,
        'total_claimed': 380.00,
        'line_items': [
            {'category': 'spa',     'description': 'Hotel spa package', 'amount': 300.00, 'receipt_attached': True},
            {'category': 'minibar', 'description': 'In-room minibar',  'amount':  80.00, 'receipt_attached': True},
        ]
    },
    {
        'claim_id': 'CLM-003',
        'purpose': 'Client site visit (business)',
        'employee': 'C. Nakamura',
        'trip_start': '2026-06-08', 'trip_end': '2026-06-10',
        'submission_date': '2026-06-22',
        'trip_days': 3,
        'total_claimed': 940.00,
        'line_items': [
            {'category': 'airfare', 'description': 'Round-trip economy airfare',   'amount': 300.00, 'receipt_attached': True, 'is_business_class': False},
            {'category': 'lodging', 'description': 'Hotel, 2 nights @ $250',      'amount': 500.00, 'receipt_attached': True, 'days': 2},
            {'category': 'meals',   'description': 'Meals, 2 days @ $70/day',     'amount': 140.00, 'receipt_attached': True, 'days': 2},
        ]
    },
    {
        'claim_id': 'CLM-004',
        'purpose': 'International vendor negotiation (business)',
        'employee': 'D. Fischer',
        'trip_start': '2026-06-16', 'trip_end': '2026-06-18',
        'submission_date': '2026-06-28',
        'trip_days': 3,
        'total_claimed': 3000.00,
        'line_items': [
            {'category': 'airfare', 'description': 'Business-class international airfare', 'amount': 2400.00, 'receipt_attached': True,  'is_business_class': True},
            {'category': 'lodging', 'description': 'Hotel, 3 nights',                    'amount':  600.00, 'receipt_attached': False, 'days': 3},
        ]
    },
    {
        'claim_id': 'CLM-005',
        'purpose': 'Client dinner / business development',
        'employee': 'E. Haddad',
        'trip_start': '2026-06-11', 'trip_end': '2026-06-11',
        'submission_date': '2026-06-24',
        'trip_days': 1,
        'total_claimed': 220.00,
        'line_items': [
            {'category': 'meals', 'description': 'Client dinner for 4 (business development)', 'amount': 220.00, 'receipt_attached': False, 'days': 1},
        ]
    }
]
