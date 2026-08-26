"""Control candidate for the pinned k-server evaluator."""


class Potential:
    def __init__(self, context, **kwargs):
        self.context = context

    def __call__(self, wf):
        return 0.0
