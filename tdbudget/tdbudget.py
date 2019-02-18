import click
import json
import os
import subprocess
import sys
from pkg_resources import Requirement, resource_filename

from .keys import *

BUDGET_PATH = os.path.join(os.path.expanduser("~"), ".tdbudget", "budget.json")
CONF_PATH = resource_filename(Requirement.parse("tdbudget"), os.path.join("tdbudget", "conf.json"))
RED = '[31m{}[0m'
GREEN = '[32m{}[0m'

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
    budget_file = open(BUDGET_PATH, "r+")
    budget = json.load(budget_file)
    budget_file.close()

    return budget

def write_budget(new_budget):
    with open(BUDGET_PATH, "w+") as budget_file:
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
    if budget["slush"] <= 0:
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
@click.option('-c', '--category', multiple=True)
def check(category):
    budget = get_budget()
    # Check all categories if none specified
    if not category:
        category = [item[NAME] for item in budget[LONG_TERM]] + [item[NAME] for item in budget[MONTHLY]]

    # Print out slush funds if they ask for them
    if SLUSH in category:
        print("You have {} in free funds".format(budget[SLUSH]))
        return

    # Collect triplets of name, contribution, target for each category
    descriptions = []
    for cat in category:
        defn = category_defn(budget, cat)
        descriptions.append((defn[CATEGORY_NAME], str(defn[CONTRIBUTION]), str(defn[TARGET])))

    # Properly space out the header so it contain the longest category name
    max_name_len = max([len(desc[0]) for desc in descriptions]) + 1
    header = "NAME "
    if max_name_len - len(header) > 0:
        padding = max_name_len - len(header)
        header += " " * padding
    header += "| CONTRIBUTION | TARGET"
    print(header)

    # Format each row and print
    for desc in descriptions:
        # Add padding to the name
        row = desc[0]
        if max_name_len - len(row) > 0:
            padding = max_name_len - len(row)
            row += " " * padding
        row += "| "

        # Add less robust padding to the contribution
        truncated_contribution = '%.3f' % float(desc[1])
        row += truncated_contribution
        row += " " * (len("CONTRIBUTION ") - len(truncated_contribution)) # @hack
        row += "| "

        # Add the target
        row += desc[2]

        # Red if over target, green if under
        if float(desc[1]) > float(desc[2]):
            print(RED.format(row))
        elif float(desc[1]) <= float(desc[2]):
            print(GREEN.format(row))
            
cli.add_command(check)


@cli.command()
@click.option('-m', '--monthly', is_flag=True)
@click.option('-l', '--longterm', is_flag=True)
@click.option('-c', '--category', multiple=True)
def clear(monthly, longterm, category):
    budget = get_budget()
    
    # clear all categories if none specified
    if not category:
        category = [item[NAME] for item in budget[LONG_TERM]] + [item[NAME] for item in budget[MONTHLY]]
        
    # Grab the block the user specified
    block = None
    if monthly:
        block = budget[MONTHLY]
    elif longterm:
        block = budget[LONG_TERM]
    else:
        click.echo("You must specify either monthly or longterm")
        return

    # Delete the items
    for cat in category:
        try:
            # Do 'found' stuff to avoid invalidating iterator
            found = False
            for idx, item in enumerate(block):
                if item[CATEGORY_NAME] == cat:
                    del block[idx]
                    found = True
                    break
                
            if found:
                continue
        except Exception as e:
            click.echo("Couldn't find category {}".format(cat))

    write_budget(budget)
        
cli.add_command(clear)

@cli.command()
def test():
    click.echo(RED.format("test"))

cli.add_command(test)

@cli.command()
def init():
    # Make the budget where generated reports will go (~/.tdbudget)
    home = os.path.expanduser("~")
    if home.endswith('/'):
        home = home[:-1]
        
    try:
        os.mkdir(os.path.join(home, ".tdbudget"))
    except:
        print("setup had problems making the directory " + os.path.join(home, ".tdbudget"))
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

        with open(CONF_PATH, "r+") as conf_file:
            conf = json.load(conf_file)
            conf[MONTH_START] = int(day)
            print(conf)
            conf_file.write(json.dumps(conf))
            
        script = 'schtasks.exe /create /tn \"tdbudget_monthly\" /tr \"{} {}\" /st 19:03 /sc MONTHLY /D {}'\
                     .format(
                         sys.executable,\
                         resource_filename(Requirement.parse("tdbudget"), os.path.join("tdbudget", "monthly.py")),\
                         day)
        print(script)

        subprocess.run(script)

cli.add_command(init)


@click.command()
@click.option('-i', '--item', nargs=2)
def conf(item):
    with open(CONF_PATH, "w+") as conf_file:
        conf = json.load(conf_file)
        conf[item[0]] = item[1]
        conf_file.write(conf)

cli.add_command(conf)
              
              
def main():
    cli()

if __name__ == "__main__":
    cli()

        
