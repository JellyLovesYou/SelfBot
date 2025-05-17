from datetime import datetime
import random


def generate_random_birthday(age: int) -> datetime:
    today = datetime.now()
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)

    if birth_month == 2 and birth_day > 29:
        birth_day = 29 if (birth_year % 4 == 0 and (birth_year % 100 != 0 or birth_year % 400 == 0)) else 28

    return datetime(birth_year, birth_month, birth_day)


def generate_random_age(min_age: int = 1, max_age: int = 100) -> int:
    return random.randint(min_age, max_age)


def feet_and_inches_to_cm(feet: int, inches: int) -> float:
    return (feet * 12 + inches) * 2.54


def get_balance() -> int:
    heads_count = sum(random.choice([0, 1]) for _ in range(3))

    if heads_count == 0:
        balance = random.randint(1, 100)
    elif heads_count == 1:
        balance = random.randint(100, 1000)
    elif heads_count == 2:
        balance = random.randint(1000, 10000)
    else:
        balance = random.randint(10000, 100000000)

    return balance


def get_height() -> str:
    flips = [random.choice([0, 1]) for _ in range(2)]
    heads_count = sum(flips)

    if heads_count == 0:
        min_height = 1
        max_height = 4
    elif heads_count == 1:
        min_height = 4
        max_height = 6
    else:
        min_height = 6
        max_height = 8

    selected_height = random.randint(min_height, max_height)
    inches = random.randint(1, 11)
    height_cm = feet_and_inches_to_cm(selected_height, inches)

    height = f"{selected_height}' {inches}\" (cm: {height_cm:.1f})"
    return height
