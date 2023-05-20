from optimus_api import TestingService
from munch import DefaultMunch
import yaml
import random
import copy


class TransformationPass(object):
    def __init__(self):
        ...

available_passes = {
    'LoopInvariant': ' -ftransforms=loop_invariant ',
    'ConstantPropagation': ' -ftransforms=const_propagation ',
    'UnusedDeclarations': ' -ftransforms=unused_declarations ',
    'FullUnrolling': ' -ftransforms=full_unrolling ',
    'LoopUnrolling': ' -ftransforms=unrolling ',
    'ArithmeticExpansion': ' -ftransforms=arithmetic_exp ',
    'ExpressionSimplifier': ' -ftransforms=expr_simplifier ',
    'FullInlining': ' -ftransforms=full_inlining ',
    'LoopNesting': ' -ftransforms=nesting '
}


class SearchingOptimizer(object):
    def __init__(self):
        self.loadConfig()
        self.service = TestingService(self.config.url, self.config.username, self.config.password, self.config.settings)
        self.history = [
            {
                "args": "",
                "passes": [],
                "runtime": -1,
            }
        ]
        self.currentPasses = []

    def getNextPasses(self, history):
        lastTry = copy.copy(history[len(history) - 1]["passes"])
        lastTry.append(random.choice(list(available_passes.keys())))
        return lastTry


    def loadConfig(self):
        with open("config.yml", "r") as stream:
            try:
                obj = yaml.safe_load(stream)
                self.config = DefaultMunch.fromDict(obj)
            except yaml.YAMLError as exc:
                print(exc)

    def optimize(self, text, iterations):
        for i in range(0, iterations):
            self.oneStep()

    def getExtraArgs(self, passes):
        args = []
        for p in passes:
            args.append(available_passes[p])
        return " ".join(args)

    def oneStep(self):
        self.currentPasses = self.getNextPasses(self.history)
        extraCmdArg = self.getExtraArgs(self.currentPasses)
        h = self.service.sendOPSTask(extraCmdArg, text)
        ok = self.service.waitTaskFinish(h)
        if (ok):
            runtime = self.service.getTaskRunTime(h)
        else:
            runtime = -1
        stepResult = {
            "args": extraCmdArg,
            "passes": self.currentPasses,
            "runtime": runtime,
        }
        print(stepResult)
        self.history.append(stepResult)




if __name__ == "__main__":

    searcher = SearchingOptimizer()
    with open('test_program.c') as input_program:
        text = input_program.read()
        searcher.optimize(text, 10)
    print(searcher.history)
