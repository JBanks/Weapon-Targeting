#!/usr/bin/env python3

if __package__ is not None and len(__package__) > 0:
    print(f"{__name__} using relative import inside of {__package__}")
    from . import simulator as sim
    from . import features as jf
    from . import problem_generators as pg
    from . import solvers as js
    from . import genetic_algorithm as jg
    from . import branch_bound as bb
else:
    import simulator as sim
    import features as jf
    import problem_generators as pg
    import solvers as js
    import genetic_algorithm as jg
    import branch_bound as bb
import numpy as np
import time
import csv
import os
import argparse
from functools import partial

TOKEN_LENGTH = 5


def solver(quantity, directory, start_idx=0, prefix="", suffix="", digits=5, Random=False, Greedy=False, AStar=False, csvfilename=None):

    # ensure that at least one solver was selected in the args
    assert (Random or Greedy or AStar), "At least one solver must be selected. Solvers are Random, Greedy, and AStar"

    # set up the solvers
    solvers = [{'name': "Random Choice", 'function': js.random_solution, 'solve': Random},
               {'name': "Greedy", 'function': js.greedy, 'solve': Greedy},
               {'name': "AStar", 'function': js.AStar, 'solve': AStar}]

    # set up CSV filename if not provided
    if csvfilename is None:
        csvfilename = f'solutions_{prefix}{suffix}'.replace("__", "_")
    # save solutions as CSV file
    csvfilename = os.path.join(directory, f'{csvfilename}.csv')

    # prepare the CSV file
    csv_content = []
    csv_row = ["filename", "total reward"]
    for solver in solvers:
        if solver['solve']:
            csv_row.append(solver['name'])
            csv_row.append(f'{csv_row[-1]} runtime')
    csv_row.append("solution")
    with open(csvfilename, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(csv_row)

    for i in range(start_idx, start_idx+quantity):
        try:
            # load the appropriate problem from the file
            filename = prefix + str(i).zfill(digits) + suffix + ".json"
            simProblem = pg.loadProblem(os.path.join(directory, filename))

            # determine problem stats
            selectable_opportunities = np.sum(simProblem['Opportunities'][:, :, jf.OpportunityFeatures.SELECTABLE])
            rewards_available = sum(simProblem['Targets'][:, jf.TaskFeatures.VALUE])

            # solve problem using all selected solvers
            csv_row = [filename, rewards_available]
            for solver in solvers:
                if solver['solve']:
                    start_time = time.time()
                    g, solution = solver['function'](simProblem)
                    total_time = start_time - time.time()
                    csv_row.append((rewards_available-g))
                    csv_row.append(total_time)
                    print(f"Total time to solve problem {i} using {solver['name']}:\n{total_time}")

            # record the last generated solution (should usually be from A*) in the CSV file
            # this is done at each step to avoid losing data if the solvers hangs on a problem
            csv_row.append(solution)
            with open(csvfilename, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(csv_row)

        # allow keyboard interrupts
        except KeyboardInterrupt:
            input("Press Enter to attempt again, or ctrl+c to quit.")


def generate_dataset(effectors, targets, quantity, solve_problems=False, directory_arg=None, prefix="", suffix="", digits=5):
    """
    Generates a dataset in a given directory with given parameters
    """
    solvers = [{'name': "Random Choice", 'function': js.random_solution, 'solve': False},
               {'name': "Greedy", 'function': js.greedy, 'solve': False},
               {'name': "AStar", 'function': js.AStar, 'solve': True}] #AStar should be the last so that its solution get printed

    #set up the appropriate directory to use
    if directory_arg is not None:
        directory = directory_arg
    else:
        directory = f"{effectors}x{targets}"
    try:
        os.mkdir(directory)
    except:
        pass

    csv_content = []
    csv_row = ["filename", "total reward"]
    for solver in solvers:
        if solver['solve']:
            csv_row.append(solver['name'])
    csv_row.append("solution")

    for i in range(quantity):
        try:
            filename = prefix + str(i).zfill(digits) + suffix + ".json"
            simProblem = pg.network_validation(effectors, targets)
            while (np.sum(simProblem['Opportunities'][:,:,jf.OpportunityFeatures.SELECTABLE]) < 1):
                simProblem = pg.network_validation(effectors, targets)
            sim.saveProblem(simProblem, os.path.join(directory, filename))

            rewards_available = sum(simProblem['Targets'][:, jf.TaskFeatures.VALUE])
            selectable_opportunities = np.sum(simProblem['Opportunities'][:, :, jf.OpportunityFeatures.SELECTABLE])
            log(f"Scenario {filename[:-5]} with {selectable_opportunities} selectable opportunities")

            if solve_problems:
                csv_row = [filename, rewards_available]
                start_time = time.time()
                for solver in solvers:
                    if solver['solve']:
                        g, solution = solver['function'](simProblem)
                        csv_row.append(g)
                end_time = time.time()
                csv_row.append(solution)

                csv_content.append(csv_row)
                log(f"Solved {i+1}/{quantity}: {filename} in: {end_time - start_time:.6f}s")
        except KeyboardInterrupt:
            input("Press Enter to attempt again, or ctrl+c to quit.")
    print()

    if solve_problems:
        csvfilename = os.path.join(directory, f'{time.time()}.csv')
        with open(csvfilename, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
        log(f"solutions exported to {csvfilename}")


def log(string):
    print(f"[{time.asctime()}] {string}")


if __name__ == '__main__':
    solvers = [{'name': "Random Choice", 'function': js.random_solution, 'solve': False},
               {'name': "Greedy", 'function': js.greedy, 'solve': False},
               {'name': "GA",
                'function': partial(jg.jfa_ga_solver, population_size=240, generations_qty=15000),
                'solve': False},
               {'name': "Branch and Bound", 'function': bb.jfa_branch_bound_solver, 'solve': True},
               {'name': "A*", 'function': js.AStar, 'solve': True}]
    # AStar should be the last solver so that its solution get printed
    parser = argparse.ArgumentParser()
    parser.add_argument('--effectors', type=int, help="The number of effectors in each problem", default=3,
                        required=False)
    parser.add_argument('--targets', type=int, help="The number of targets in each problem", default=9, required=False)
    parser.add_argument('--quantity', type=int, help="The number of problems of each size", default=1, required=False)
    parser.add_argument('--offset', type=int, help="Numbering offset for scenarios", default=0, required=False)
    parser.add_argument('--solve', type=bool, help="Whether or not we will solve the problems", default=True,
                        required=False)
    parser.add_argument('--save', type=bool, help="Save the output to a file", default=False, required=False)
    args = parser.parse_args()
    effectors = args.effectors
    targets = args.targets
    num_problems = args.quantity
    numbering_offset = args.offset
    solve_problems = args.solve
    save = args.save
    # directory = f"{effectors}x{targets}"
    directory = os.path.join(f"JFA Validation Datasets for DRDC Slides", f"JFA {effectors}x{targets} Validation Set")
    try:
        os.mkdir(directory)
    except Exception as error:
        pass
    csv_content = []
    csv_row = ["filename", "total reward"]
    for solver in solvers:
        if solver['solve']:
            csv_row.append(solver['name'])
            csv_row.append('time (s)')
    csv_row.append("solution")
    csv_content.append(csv_row)
    for i in range(numbering_offset, num_problems + numbering_offset):
        try:
            identifier = f"validation_{i:05d}_{effectors}x{targets}"
            filename = identifier + ".json"
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                simProblem = sim.loadProblem(filepath)
            else:
                simProblem = pg.network_validation(effectors, targets)
                while np.sum(simProblem['Opportunities'][:, :, jf.OpportunityFeatures.SELECTABLE]) < 1:
                    simProblem = pg.network_validation(effectors, targets)
                sim.saveProblem(simProblem, filepath)

            rewards_available = sum(simProblem['Targets'][:, jf.TaskFeatures.VALUE])
            selectable_opportunities = np.sum(simProblem['Opportunities'][:, :, jf.OpportunityFeatures.SELECTABLE])
            log(f"Scenario {filename[:-5]} with {selectable_opportunities} selectable opportunities")

            if solve_problems:
                csv_row = [filename, rewards_available]
                start_time = time.time()
                recent_time = start_time
                solution = []
                for solver in solvers:
                    if solver['solve']:
                        g, solution = solver['function'](simProblem)
                        log(f"solution for {solver['name']}: {solution}: {g}")
                        csv_row.append(g)
                        current_time = time.time()
                        csv_row.append(current_time - recent_time)
                end_time = time.time()
                csv_row.append(solution)

                csv_content.append(csv_row)
                log(f"Solved {i+1}/{num_problems+numbering_offset}: {filename} in: {end_time - start_time:.6f}s")
        except KeyboardInterrupt:
            input("Press Enter to attempt again, or ctrl+c to quit.")
    print()

    if solve_problems and save:
        csv_filename = os.path.join(directory, f'{time.time()}.csv')
        with open(csv_filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
        log(f"solutions exported to {csv_filename}")
