import re
from decimal import Decimal


ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫",
    "01234567890123456789,.",
)
MARINA = re.compile(r"\b(?:dubai\s+marina|marina|دبي\s+مارينا|مارينا)\b", re.I)
TWO_BEDROOMS_AR = re.compile(r"\b(?:ب?غرفت[يي]ن?|غرفتا)\s+نوم\b")
BEDROOMS = re.compile(
    r"\b([1-5]|one|two|three|four|five)[ -]*(?:br|beds?|bedrooms?)\b", re.I
)
BUDGET = re.compile(
    r"(?:\b(?:up to|under|maximum budget(?: is)?|budget(?: is)?|بميزانية|"
    r"الميزانية|بحد أقصى)\b)\s*[:=]?\s*(?:AED\s*)?"
    r"(\d[\d,]*(?:\.\d+)?)\s*(million|millions|مليون|ملايين|ألف|الف|[mk])?"
    r"(?!\w|[.,]\d)",
    re.I,
)
MULTIPLIERS = {
    "m": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "مليون": 1_000_000,
    "ملايين": 1_000_000,
    "k": 1_000,
    "ألف": 1_000,
    "الف": 1_000,
}


def extract_buyer_requirements(inquiry):
    text = inquiry.translate(ARABIC_DIGITS)
    area = "Dubai Marina" if MARINA.search(text) else ""
    bedrooms = 0
    bedroom_match = BEDROOMS.search(text)

    if bedroom_match:
        value = bedroom_match[1].lower()
        words = ("one", "two", "three", "four", "five")
        bedrooms = int(value) if value.isdigit() else words.index(value) + 1
    elif TWO_BEDROOMS_AR.search(text):
        bedrooms = 2

    budget_aed = 0
    budget_match = BUDGET.search(text)
    if budget_match:
        amount = Decimal(budget_match[1].replace(",", ""))
        suffix = (budget_match[2] or "").lower()
        budget_aed = int(amount * MULTIPLIERS.get(suffix, 1))

    return area, bedrooms, budget_aed


def qualify_buyer(inquiry):
    area, bedrooms, budget_aed = extract_buyer_requirements(inquiry)
    required_fields = (
        (area, "Which area are you looking to buy in?"),
        (bedrooms, "How many bedrooms do you need?"),
        (budget_aed, "What is your maximum purchase budget in AED?"),
    )

    for value, question in required_fields:
        if not value:
            return "Needs clarification", question

    return "Sales queue", "Qualified buyer ready for broker review."


if __name__ == "__main__":
    inquiry = input("Paste a buyer inquiry: ")
    print("Extracted:", extract_buyer_requirements(inquiry))
    print("Decision:", qualify_buyer(inquiry))