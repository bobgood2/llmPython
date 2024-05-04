import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _1 = _C0 = _C1 = _return_value = a = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_email(9, 0, _id='_C0')

    def _concurrent_G1():
        nonlocal _1, _C0, _C1, a
        a = [_C0.Result, 2]
        _1 = a[1]
        _C1 = orchestrator.search_email(_1, _id='_C1')

    def _concurrent_G2():
        nonlocal _C1, _return_value, a
        _return_value = _C1.Result + 1
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C1']})
    return _return_value


orchestrator.Return(_program(orchestrator))