import json
import os
import copy
from datetime import datetime
from pkg_resources import Requirement, resource_filename

from keys import *

# Shamelessly ripped from https://stackoverflow.com/questions/3424899/whats-the-simplest-way-to-subtract-a-month-from-a-date-in-python
def month_delta(date, delta):
    month = (date.month + delta) % 12
    month = month if month else 12
    year = date.year + (date.month + delta - 1) // 12
    day = min(date.day, [31, 29 if y%4==0 and not y%400==0 else 28,31,30,31,30,31,31,30,31,30,31][m-1])
    
    return date.replace(day=day ,month=month , year=year)

def monthly():
    budget_file_name = resource_filename(Requirement.parse("tdbudget"), os.path.join("tdbudget", "budget.json"))

    # Load up the budget
    budget = None
    with open(budget_file_name, "r") as budget_file:
        budget = json.load(budget_file)

    # Reset each bucket and remember the old amount
    old_budget = copy.deepcopy(budget)
    for bucket in budget[MONTHLY]:
        bucket[SAVED] = 0

    # Write out this month's savings
    date = month_delta(datetime.now(), -1)
    log_file = "{}_{}.json".format(date.month, date.year)
    with open(os.path.join(os.path.expanduser("~"), ".tdbudget", log_file), "w") as f:
        json.dump(old_budget, f, indent=4, sort_keys=True)

    # Write out the buckets with the savings cleared to 0
    with open(budget_file_name, "w") as f:
        json.dump(budget, f, indent=4, sort_keys=True)

if __name__ == "__main__":
    monthly()
