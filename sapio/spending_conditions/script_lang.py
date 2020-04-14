from __future__ import annotations

from typing import TypeVar, Generic, Any, Union, Optional

from typing_extensions import Protocol

from sapio.bitcoinlib.static_types import *
from sapio.util import methdispatch


class ClauseProtocol(Protocol):
    @property
    def a(self) -> Any:
        pass
    @property
    def b(self) -> Any:
        pass
    @property
    def n_args(self) -> int:
        return 0
    @property
    def symbol(self) -> str:
        return ""

class StringClauseMixin:
    MODE = "+"  # "str"
    def __str__(self: ClauseProtocol) -> str:
        if StringClauseMixin.MODE == "+":
            if self.__class__.n_args == 1:
                return "{}({})".format(self.__class__.__name__, self.a)
            elif self.__class__.n_args == 2:
                return "{}{}{}".format(self.a, self.symbol, self.b)
            else:
                return "{}()".format(self.__class__.__name__)
        else:
            if self.__class__.n_args == 1:
                return "{}({})".format(self.__class__.__name__, self.a)
            elif self.__class__.n_args == 2:
                return "{}({}, {})".format(self.__class__.__name__, self.a, self.b)
            else:
                return "{}()".format(self.__class__.__name__)


class SatisfiedClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 0
class UnsatisfiableClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 0


class AndClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 2
    symbol = "*"

    def __init__(self, a: AndClauseArgument, b: AndClauseArgument):
        self.a = a
        self.b = b


class OrClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 2
    symbol = "+"
    def __init__(self, a: AndClauseArgument, b: AndClauseArgument):
        self.a: AndClauseArgument = a
        self.b: AndClauseArgument = b


class SignatureCheckClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1
    def __init__(self, a: Variable[PubKey]):
        self.a = a
        self.b = a.sub_variable("signature")


class PreImageCheckClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    a : Variable[Hash]
    b : Variable[Hash]
    def __init__(self, a: Variable[Hash]):
        self.a = a
        self.b = a.sub_variable("preimage")


class CheckTemplateVerifyClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    def __init__(self, a: Variable[Hash]):
        self.a = a



class AbsoluteTimeSpec:
    def __init__(self, t):
        self.time : LockTime = t

class RelativeTimeSpec:
    def __init__(self, t):
        self.time : Sequence = t
    @staticmethod
    def from_seconds(seconds: float) -> RelativeTimeSpec:
        t = uint32((seconds + 511) // 512)
        if t > 0x0000ffff:
            raise ValueError("Time Span {} seconds is too long! ".format(seconds))
        # Bit 22 enables time based locks.
        l = uint32(1 << 22) | t
        return RelativeTimeSpec(Sequence(uint32(l)))


TimeSpec = Union[AbsoluteTimeSpec, RelativeTimeSpec]

def Weeks(n:float) -> RelativeTimeSpec:
    if n > (0xFFFF*512//60//60//24//7):
        raise ValueError("{} Week Span is too long! ".format(n))
    # lock times are in groups of 512 seconds
    seconds = n*7*24*60*60
    return RelativeTimeSpec.from_seconds(seconds)

def Days(n:float) -> RelativeTimeSpec:
    if n > (0xFFFF*512//60//60//24):
        raise ValueError("{} Day Span too long! ".format(n))
    # lock times are in groups of 512 seconds
    seconds = n*24*60*60
    return RelativeTimeSpec.from_seconds(seconds)


class AfterClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    @methdispatch
    def initialize(self, a: Variable[TimeSpec]):
        self.a = a
    @initialize.register
    def _with_relative(self, a: RelativeTimeSpec):
        self.a = Variable("", a)
    @initialize.register
    def _with_absolute(self, a: AbsoluteTimeSpec):
        self.a = Variable("", a)
    def __init__(self, a: Union[Variable[TimeSpec], TimeSpec]):
        self.initialize(a)



V = TypeVar('V')


class Variable(Generic[V]):
    def __init__(self, name: str, value: Optional[V] = None):
        self.name: str = name
        self.assigned_value: Optional[V] = value
        self.sub_variable_count = -1

    def sub_variable(self, purpose: str, value: Optional[V] = None) -> Variable:
        self.sub_variable_count += 1
        return Variable(self.name + "_" + str(self.sub_variable_count) + "_" + purpose, value)

    def assign(self, value: V):
        self.assigned_value = value

    def __str__(self):
        return "{}('{}', {})".format(self.__class__.__name__, self.name, self.assigned_value)


AndClauseArgument = Union[
               SatisfiedClause,
               UnsatisfiableClause,
               OrClause,
               AndClause,
               SignatureCheckClause,
               PreImageCheckClause,
               CheckTemplateVerifyClause,
               AfterClause]
Clause = Union[SatisfiedClause, UnsatisfiableClause,
               Variable,
               OrClause,
               AndClause,
               SignatureCheckClause,
               PreImageCheckClause,
               CheckTemplateVerifyClause,
               AfterClause]

