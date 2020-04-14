from typing import TypeVar, List, Tuple, Any, Dict

from sapio.bitcoinlib.script import CScript
from sapio.spending_conditions.opcodes import AllowedOp
from sapio.spending_conditions.script_lang import Variable, Clause, AndClause, AndClauseArgument, OrClause, \
    SignatureCheckClause, \
    PreImageCheckClause, CheckTemplateVerifyClause, AfterClause, AbsoluteTimeSpec, RelativeTimeSpec
from sapio.util import methdispatch

T = TypeVar('T')


class WitnessTemplate:
    def __init__(self):
        self.witness = []
        self.nickname = None

    def add(self, it):
        self.witness.insert(0, it)

    def name(self, nickname):
        self.nickname = nickname


class WitnessManager:
    def __init__(self):
        self.program: CScript = CScript()
        self.witnesses : Dict[Any, WitnessTemplate] = {}
    def get_witness(self, key) -> WitnessTemplate:
        return self.witnesses[key]
    def make_witness(self, key) -> WitnessTemplate:
        assert key not in self.witnesses
        self.witnesses[key] = WitnessTemplate()
        return self.witnesses[key]


class ProgramBuilder:
    def compile_cnf(self, clause: Clause) -> List[List[Clause]]:
        # TODO: Figure out how many passes are required / abort when stable
        # 1000 should be enough that covers all valid scripts...
        for x in range(1000):
            clause = self.normalize(clause)
        return self.flatten(clause)


    def compile(self, clause: Clause) -> WitnessManager:
        cnf: List[List[Clause]] = self.compile_cnf(clause)
        n_cases = len(cnf)
        witness_manager: WitnessManager = WitnessManager()

        # If we have one or two cases, special case the emitted scripts
        # 3 or more, use a generic wrapper
        if n_cases == 1:
            witness = witness_manager.make_witness(0)
            for cl in cnf[0]:
                compiled_frag = self._compile(cl, witness)
                witness_manager.program += compiled_frag
            # Hack because the fragment compiler leaves stack empty
            witness_manager.program += CScript([AllowedOp.OP_1])
        elif n_cases == 2:
            wit_0 = witness_manager.make_witness(0)
            wit_1 = witness_manager.make_witness(1)
            wit_0.add(1)
            wit_1.add(0)
            # note order of side effects!
            branch_a = CScript([self._compile(frag, wit_0) for frag in cnf[0]])
            branch_b = CScript([self._compile(frag, wit_1) for frag in cnf[1]])
            witness_manager.program = CScript([AllowedOp.OP_IF,
                                               branch_a,
                                               AllowedOp.OP_ELSE,
                                               branch_b,
                                               AllowedOp.OP_ENDIF,
                                               AllowedOp.OP_1])
        else:
            # Check that the first argument passed is an in range execution path
            # Note the first branch does not subtract one, so we have arg in [0, N)
            script = CScript([AllowedOp.OP_DUP,
                              AllowedOp.OP_0,
                              n_cases,
                              AllowedOp.OP_WITHIN,
                              AllowedOp.OP_VERIFY])
            for (idx, frag) in enumerate(cnf):
                wit = witness_manager.make_witness(idx)
                wit.add(idx)
                if idx == 0:
                    # Don't subtract one on first check
                    witness_manager.program += CScript([AllowedOp.OP_IFDUP,
                                                        AllowedOp.OP_NOTIF])
                else:
                    witness_manager.program += CScript([AllowedOp.OP_1SUB,
                                                        AllowedOp.OP_IFDUP,
                                                        AllowedOp.OP_NOTIF])

                for cl in frag:
                    script += self._compile(cl, wit)
                # We push an OP_0 onto the stack as it will cause
                # all following branches to not execute,
                # unless we are the last branch
                if idx+1 < len(cnf):
                    witness_manager.program += CScript([AllowedOp.OP_0, AllowedOp.OP_ENDIF])
                else:
                    witness_manager.program += CScript([AllowedOp.OP_ENDIF])
            # Push an OP_1 so that we succeed
            witness_manager.program += CScript([AllowedOp.Op_1])
        return witness_manager

    # Normalize Bubbles up all the OR clauses into a CNF
    @methdispatch
    def normalize(self, arg: Clause) -> Clause:
        raise NotImplementedError("Cannot Compile Arg")

    @normalize.register
    def normalize_and(self, arg: AndClause) -> Clause:
        a: AndClauseArgument = arg.a
        b: AndClauseArgument = arg.b
        if isinstance(a, OrClause) and isinstance(b, OrClause):
            a0: AndClauseArgument = a.a
            a1: AndClauseArgument = a.b
            b0: AndClauseArgument = b.a
            b1: AndClauseArgument = b.b
            return a0 * b0 + a0 * b1 + a1 * b0 + a1 * b1
        elif isinstance(b, AndClause) and isinstance(a, OrClause):
            _or, _and = a, b
            return _and * _or.a + _and * _or.b
        elif isinstance(a, AndClause) and isinstance(b, OrClause):
            _or, _and = b, a
            return _and * _or.a + _and * _or.b
        # Other Clause can be ignored...
        elif isinstance(a, AndClause):
            return AndClause(self.normalize(a), b)
        elif isinstance(a, OrClause):
            a0, a1 = a.a, a.b
            return a0 * b + a1 * b
        elif isinstance(b, AndClause):
            return AndClause(self.normalize(b), a)
        elif isinstance(b, OrClause):
            b0, b1 = b.a, b.b
            return b0 * a + b1 * a
        else:
            return arg

    @normalize.register
    def normalize_or(self, arg: OrClause) -> Clause:
        return OrClause(self.normalize(arg.a), self.normalize(arg.b))

    # TODO: Unionize!

    @normalize.register
    def normalize_signaturecheck(self, arg: SignatureCheckClause) -> Clause:
        return arg

    @normalize.register
    def normalize_preimagecheck(self, arg: PreImageCheckClause) -> Clause:
        return arg

    @normalize.register
    def normalize_ctv(self, arg: CheckTemplateVerifyClause) -> Clause:
        return arg

    @normalize.register
    def normalize_after(self, arg: AfterClause) -> Clause:
        return arg

    @normalize.register
    def normalize_var(self, arg: Variable) -> Clause:
        return arg

    @methdispatch
    def flatten(self, arg: Clause) -> List[List[Clause]]:
        raise NotImplementedError("Cannot Compile Arg")

    @flatten.register
    def flatten_and(self, arg: AndClause) -> List[List[Clause]]:
        assert not isinstance(arg.a, OrClause)
        assert not isinstance(arg.b, OrClause)
        l = self.flatten(arg.a)
        l2 = self.flatten(arg.b)
        assert len(l) == 1
        assert len(l2) == 1
        l[0].extend(l2[0])
        return l

    @flatten.register
    def flatten_or(self, arg: OrClause) -> List[List[Clause]]:
        return self.flatten(arg.a) + self.flatten(arg.b)

    @flatten.register
    def flatten_sigcheck(self, arg: SignatureCheckClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_preimage(self, arg: PreImageCheckClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_ctv(self, arg: CheckTemplateVerifyClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_after(self, arg: AfterClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_var(self, arg: Variable) -> List[List[Clause]]:
        return [[arg]]

    @methdispatch
    def _compile(self, arg: Clause, witness: WitnessTemplate) -> CScript:
        raise NotImplementedError("Cannot Compile Arg", arg)

    @_compile.register
    def _compile_and(self, arg: SignatureCheckClause, witness) -> CScript:
        return self._compile(arg.b, witness) + self._compile(arg.a, witness) + CScript([AllowedOp.OP_CHECKSIGVERIFY])

    @_compile.register
    def _compile_preimage(self, arg: PreImageCheckClause, witness) -> CScript:
        return self._compile(arg.b, witness) + \
               CScript([AllowedOp.OP_SHA256]) + self._compile(arg.a, witness) + CScript([AllowedOp.OP_EQUAL])

    @_compile.register
    def _compile_ctv(self, arg: CheckTemplateVerifyClause, witness) -> CScript:
        # While valid to make this a witness variable, this is likely an error
        assert arg.a.assigned_value is not None
        assert isinstance(arg.a.assigned_value, bytes)
        s = CScript([arg.a.assigned_value, AllowedOp.OP_CHECKTEMPLATEVERIFY, AllowedOp.OP_DROP])
        witness.name(arg.a.assigned_value)
        return s

    @_compile.register
    def _compile_after(self, arg: AfterClause, witness) -> CScript:
        # While valid to make this a witness variable, this is likely an error
        assert arg.a.assigned_value is not None
        if isinstance(arg.a.assigned_value, AbsoluteTimeSpec):
            return CScript([arg.a.assigned_value.time, AllowedOp.OP_CHECKLOCKTIMEVERIFY, AllowedOp.OP_DROP])
        if isinstance(arg.a.assigned_value, RelativeTimeSpec):
            return CScript([arg.a.assigned_value.time, AllowedOp.OP_CHECKSEQUENCEVERIFY, AllowedOp.OP_DROP])
        raise ValueError

    @_compile.register
    def _compile_var(self, arg: Variable, witness) -> CScript:
        if arg.assigned_value is None:
            # Todo: this is inefficient...
            witness.add(arg.name)
            return CScript()
        else:
            return CScript([arg.assigned_value])