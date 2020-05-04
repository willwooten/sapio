from typing import Iterator, List, Tuple

from bitcoinlib.static_types import Amount, PubKey, int64
from sapio_compiler.contract import Contract, TransactionTemplate
from sapio_compiler.contract.decorators import guarantee, require
from sapio_zoo.p2pk import PayToSegwitAddress
from bitcoin_script_compiler.clause import (AbsoluteTimeSpec, RelativeTimeSpec,
                                 SignatureCheckClause)


def add_timeout(tx, delay):
    if isinstance(delay, RelativeTimeSpec):
        tx.set_sequence(delay.time)
    elif isinstance(delay, AbsoluteTimeSpec):
        tx.set_locktime(delay.time)



class CancellableSubscription(Contract):
    class Fields:
        amount: Amount
        recipient: PayToSegwitAddress
        schedule: List[Tuple[AbsoluteTimeSpec, Amount]]
        return_address: PayToSegwitAddress
        watchtower_key: PubKey
        return_timeout: RelativeTimeSpec
    class MetaData:
        color = lambda self: "blue"
        label = lambda self: "Cancellable Subscription"
    @guarantee
    def cancel(self):
        tx = TransactionTemplate()
        amount = self.amount.assigned_value
        cc = CancelContest(
            amount=amount,
            recipient=self.recipient,
            schedule=self.schedule,
            return_address=self.return_address,
            watchtower_key=self.watchtower_key,
            return_timeout=self.return_timeout)
        tx.add_output(amount, cc)
        return tx

    @guarantee
    def claim(self):
        tx = TransactionTemplate()
        (delay, amount) = self.schedule.assigned_value[0]
        add_timeout(tx, delay)

        total_amount = self.amount.assigned_value
        tx.add_output(amount, self.recipient.assigned_value)

        if len(self.schedule.assigned_value) > 1:
            new_amount = total_amount - amount
            tx.add_output(new_amount,
                          CancellableSubscription(amount=new_amount,
                                                  recipient=self.recipient,
                                                  schedule=self.schedule.assigned_value[1:],
                                                  watchtower_key=self.watchtower_key,
                                                  return_timeout=self.return_timeout,
                                                  return_address=self.return_address))
        return tx

class CancelContest(Contract):
    class Fields:
        amount: Amount
        recipient: Contract
        schedule: List[Tuple[AbsoluteTimeSpec, Amount]]
        return_address: Contract
        watchtower_key: PubKey
        return_timeout: RelativeTimeSpec
    class MetaData:
        color = lambda self: "red"
        label = lambda self: "Cancellation Attempt"

    @require
    def watchtower_selects_best(self):
        return SignatureCheckClause(self.watchtower_key)

    @watchtower_selects_best
    @guarantee
    def counterclaim(self) -> Iterator[TransactionTemplate]:
        amount_earned = Amount(int64(0))
        for (timeout, amount) in self.schedule.assigned_value:
            amount_earned += amount
            amount_refundable = self.amount.assigned_value-amount_earned
            tx = TransactionTemplate()
            add_timeout(tx, timeout)
            tx.add_output(amount_earned, self.recipient.assigned_value)
            if amount_refundable:
                tx.add_output(amount_refundable, self.return_address.assigned_value)
            yield tx
    @guarantee
    def finish_cancel(self):
        tx = TransactionTemplate()
        tx.set_sequence(self.return_timeout.assigned_value.time)
        amount = self.amount.assigned_value
        return_address = self.return_address.assigned_value
        tx.add_output(amount, return_address)
        return tx


class auto_pay:
    class Fields:
        period: int
        per_time: Amount
        times: int
        recipient: PayToSegwitAddress
        return_address: PayToSegwitAddress
        watchtower_key: PubKey
        return_timeout: RelativeTimeSpec


    @classmethod
    def create_instance(cls, **kwargs) -> CancellableSubscription:
        period = kwargs.pop('period')
        times = kwargs.pop('times')
        per_time = kwargs.pop('per_time')
        kwargs['schedule'] = [(AbsoluteTimeSpec.at_height((t+1)*period), per_time) for t in range(times)]
        kwargs['amount'] = per_time*times
        return CancellableSubscription(**kwargs)