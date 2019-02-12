import click
import json
import os
import subprocess
import sys
from pkg_resources import Requirement, resource_filename

from .keys import *

BUDGET_PATH = os.path.join(os.path.expanduser("~"), ".tdbudget", "budget.json")
CONF_PATH = resource_filename(Requirement.parse("tdbudget"), os.path.join("tdbudget", "conf.json"))

def category_defn(budget, category_name):
    is_monthly = [category for category in budget[MONTHLY] if category[CATEGORY_NAME] == category_name]
    is_long_term = [category for category in budget[LONG_TERM] if category[CATEGORY_NAME] == category_name]

    if is_monthly:
        assert len(is_monthly) is 1
        assert len(is_long_term) is 0
        return is_monthly[0]
    elif is_long_term:
        assert len(is_long_term) is 1
        assert len(is_monthly) is 0
        return is_long_term[0]
    else:
        return None

def get_budget():
    # Load the current budget data
    budget_file = open(BUDGET_PATH, "r")
    budget = json.load(budget_file)
    budget_file.close()

    return budget

def write_budget(new_budget):
    with open(BUDGET_PATH, "w") as budget_file:
        json.dump(new_budget, budget_file, indent=4, sort_keys=True)

        
@click.group()
def cli():
    pass


@cli.command()
@click.argument('category')
@click.argument('amount')
def spend(category, amount):
    budget = get_budget()

    # Get the block corresponding to this category and add the new $
    defn = category_defn(budget, category)
    defn[CONTRIBUTION] += float(amount)

    budget["slush"] -= float(amount)
    if not budget["slush"] < 0:
        print("Whoa there. You've spent more money than you brought in. Just letting you know.")
    
    write_budget(budget)

cli.add_command(spend)


@cli.command()
@click.argument('amount')
def save(amount):
    budget = get_budget()
    budget["slush"] += float(amount)
    write_budget(budget)

cli.add_command(save)


@cli.command()
def add():
    # Get name of category
    category = input("What's the name of the category?: ")

    # Monthly or long-term
    kind = None
    while kind != "l" and kind != "m":
        kind = input("Is this a long-term goal or a monthly goal? [l/m]: ")

    # Get contribution target
    target = float(input("What's your contribution target?: "))

    # Get the end date if it's on a deadline
    if kind == "l":
        date = input("When's the deadline? [MM/DD/YYYY]: ")

    # Write it out to JSON
    budget = get_budget()
    if kind == "l":
        budget[LONG_TERM].append({
            CATEGORY_NAME: category,
            CONTRIBUTION: 0,
            TARGET: target,
            DATE: date
        })
    elif kind == "m":
        budget[MONTHLY].append({
            CATEGORY_NAME: category,
            CONTRIBUTION: 0,
            TARGET: target,
        })

    write_budget(budget)

cli.add_command(add)


@cli.command()
@click.argument('category')
def check(category):
    budget = get_budget()
    if category == SLUSH:
        print("You have {} in free funds".format(budget[SLUSH]))
        return

    defn = category_defn(budget, category)
    print('You have contributed {} out of a target of {} to the category "{}"'.format(\
            str(defn[CONTRIBUTION]), str(defn[TARGET]), defn[CATEGORY_NAME]))
          
cli.add_command(check)

@cli.command()
def init():
    # Make the budget where generated reports will go (~/.tdbudget)
    home = os.path.expanduser("~")
    if home.endswith('/'):
        home = home[:-1]
        
    try:
        os.mkdir(os.path.join(home, ".tdbudget"))
    except:
        "setup had problems making the directory " + os.path.join(home, ".tdbudget")
        pass

    # Make the budget file
    budget = {
        MONTHLY: [],
        LONG_TERM: [],
        SLUSH: 0
    }
    write_budget(budget)

    # Check that the user is ok with us installing a cronjob
    val = None
    while val != "y" and val != "n":
        val = input("tdbudget will install a cronjob to reset monthly savings targets and generate a report. Do you want to continue? [y/n]: ")

    # Install the cronjob
    if val == "y":
        day = input("What day of the month do you want to use as a delimiter? Please enter a single number between 1 and 28: ")
        print('You can change this later with "tdbudget conf month_start X"')

        with open(CONF_PATH, "w") as conf_file:
            conf = json.load(conf_file)
            conf[MONTH_START] = int(day)
            conf_file.write(conf)
            
        script = 'schtasks.exe /create /tn \"tdbudget_monthly\" /tr \"{} {}\" /st 19:03 /sc MONTHLY /D {}'\
                     .format(
                         sys.executable,\
                         resource_filename(Requirement.parse("tdbudget"), os.path.join("tdbudget", "monthly.py")),\
                         day)
        print(script)

        subprocess.run(script)

cli.add_command(init)


@click.command()
def conf(key, value):
    with open(CONF_PATH, "w") as conf_file:
        conf = json.load(conf_file)
        conf[key] = value
        conf_file.write(conf)
        
cli.add_command(conf)
              
              
def main():
    cli()

if __name__ == "__main__":
    cli()

        
