#!/usr/bin/env python3

import heapq
import SampleSimulator as Sim
import ProblemGenerators as PG
import JFAFeatures as JF
import numpy as np
import copy
import time


class Node:
    """
    This node class is used to simplify storage and comparisson between different
    states that are reached by the search algorithm.
    """
    def __init__(self, g, action, state, reward, terminal=False):
        self.g = g
        self.action = action
        self.state = state
        self.reward = reward
        self.terminal = terminal

    def __eq__(self, other):
        if type(other) == type(self):
            if (self.state['Effectors'] != other.state['Effectors']).any():
                return False
            if (self.state['Targets'] != other.state['Targets']).any():
                return False
            if (self.state['Opportunities'] != other.state['Opportunities']).any():
                return False
            return True
        else:
            if (self.state['Effectors'] != other['Effectors']).any():
                return False
            if (self.state['Targets'] != other['Targets']).any():
                return False
            if (self.state['Opportunities'] != other['Opportunities']).any():
                return False
            return True

    def __lt__(self, other):
        if type(other) == type(self):
            return self.g < other.g
        else:
            return self.g < other

    def __gt__(self, other):
        if type(other) == type(self):
            return self.g > other.g
        else:
            return self.g > other

    def Parent(self, parent):
        self.parent = parent

    def Solution(self):
        solution = ''
        if self.action == None:
            return solution
        if hasattr(self, 'parent'):
            solution += self.parent.Solution() + ','
        return solution + f"{self.action}"


def astar_heuristic(state):
    """
    This heuristic is naive and assumes that we can get all of the rewards available to an effector.
    This will extend the search space significantly, but should guarantee the optimal solution.
    The heuristic is optimistic, and assumes that the same effector can more targets than it is capable of.
    """
    remaining_reward = 0
    for i, target in enumerate(state['Targets']):
        if target[JF.TaskFeatures.SELECTED] == 1:
            continue  # This task has already been selected the maximum number of times.
        remaining_moves = int(min((1 - target[JF.TaskFeatures.SELECTED]) * 2,
                                  sum(state['Opportunities'][:, i, JF.OpportunityFeatures.SELECTABLE] * 2)))
        if not remaining_moves:
            continue  # The minimum between the number of hits left on a target, and eligible effectors is zero.
        value = target[JF.TaskFeatures.VALUE]
        top = np.argpartition(state['Opportunities'][:, i, JF.OpportunityFeatures.PSUCCESS], -1)[
               -1:]  # select the top 'n' effectors.
        for move in range(remaining_moves):
            reward = value * state['Opportunities'][top[0], i, JF.OpportunityFeatures.PSUCCESS]
            remaining_reward += reward
            value -= reward
    return remaining_reward  # Return the remaining reward if all moves were possible.


def AStar(state, heuristic=astar_heuristic):
    """
    This is an A* implementation to search for a solution to a given JFA problem.
    """
    node = Node(sum(state['Targets'][:, JF.TaskFeatures.VALUE]), None, state, 0)
    expansions = 0
    branchFactor = 0
    duplicate_states = 0
    frontier = []
    explored = []
    heapq.heappush(frontier, node)
    while frontier:
        node = heapq.heappop(frontier)
        if node in explored:
            continue
        # print(f"pulled g: {node.g}, action: {node.action}")
        expansions += 1
        print(f"\rExpansions: {expansions}, Duplicates: {duplicate_states}", end="")
        if hasattr(node, 'parent'):
            if node.terminal is True:
                print(f"\nTerminal node pulled: g = {node.g}")
                if node.g == node.parent.g - node.reward:
                    return node.Solution(), node.g, expansions, branchFactor
                print(f"Sending node back to heap. g: {node.g} -> {node.parent.g - node.reward}")
                node.g = node.parent.g - node.reward
                heapq.heappush(frontier, node)
                continue
            node.g = node.parent.g - node.reward
            ## This may actually not be the optimal.  There may be a more optimal node.
            ## If the value is the same, we found it, if the value changes, put it back in the heap.
        explored.append(node)
        state = node.state
        for effector, target in np.stack(
                np.where(state['Opportunities'][:, :, JF.OpportunityFeatures.SELECTABLE] == True), axis=1):
            action = (effector, target)
            new_state, reward, terminal = env.update_state(action, copy.deepcopy(state))
            g = node.g - reward  # The remaining value after the action taken
            h = heuristic(new_state)  # The possible remaining value assuming that all of the best actions can be taken
            child = Node(g - h, action, new_state, reward, terminal)
            child.Parent(node)
            if child not in explored and child not in frontier:
                heapq.heappush(frontier, child)
                branchFactor += 1
                # print(f"push {child.g} <- ({g}-{h}), action: {action}")
            # elif child in frontier and child.g < frontier[frontier.index(child)].g:
            #    # This shouldn't ever happen.  If we end up in the same state, then we should have the same reward.  must be a floating point bug.
            #    print(f"state updated.  That's weird... g changed from {child.g} to {frontier[frontier.index(child)].g}")
            #    heapq.heappush(frontier, child)
            else:
                duplicate_states += 1
    return "failed", None, expansions, branchFactor


def ucs_heuristic(state):
    return 0


if __name__ == '__main__':
    env = Sim.Simulation(Sim.state_to_dict)
    simProblem = PG.toy()
    state = env.reset(simProblem)  # get initial state or load a new problem
    print(f"Problem size: {(len(state['Effectors']), len(state['Targets']))}")
    # Sim.printState(Sim.MergeState(env.effectorData, env.taskData, env.opportunityData))
    rewards_available = sum(state['Targets'][:, JF.TaskFeatures.VALUE])
    print("A-Star")
    astar_start_time = time.time()
    solution, g, expansions, branchFactor = AStar(state)
    astar_end_time = time.time()
    # print("\nUCS")
    # ucs_start_time = time.time()
    # ucs_solution, ucs_g, ucs_expansions, ucs_branchFactor = AStar(state, heuristic=ucs_heuristic)
    # ucs_end_time = time.time()
    Sim.printState(Sim.mergeState(env.effectorData, env.taskData, env.opportunityData))
    print(f"{(len(state['Effectors']), len(state['Targets']))}")
    print(
        f"AStar solved in: {astar_end_time - astar_start_time:.6f}s, Expansions: {expansions}, branchFactor: {branchFactor}, Reward left: {g} / {rewards_available}, Steps: {solution}")
    # print(
    #    f"UCS solved in: {ucs_end_time - ucs_start_time:.6f}s, Expansions: {ucs_expansions}, branchFactor: {ucs_branchFactor}, Reward left: {ucs_g} / {rewards_available}, Steps: {ucs_solution}")
