use bitcoin::util::amount::CoinAmount;
use sapio::contract::*;
use sapio::*;
use sapio_base::timelocks::RelTime;
use sapio_base::Clause;
use std::convert::{TryFrom, TryInto};
pub struct TrustlessEscrow {
    alice: bitcoin::PublicKey,
    bob: bitcoin::PublicKey,
    alice_escrow: (CoinAmount, bitcoin::Address),
    bob_escrow: (CoinAmount, bitcoin::Address),
}

impl TrustlessEscrow {
    guard! {
        fn cooperate(self, ctx) {
            Clause::And(vec![Clause::Key(self.alice), Clause::Key(self.bob)])
        }
    }
    then! {
        fn use_escrow(self, ctx) {
            ctx.template()
                .add_output(
                    self.alice_escrow.0.try_into()?,
                    &Compiled::from_address(self.alice_escrow.1.clone(), None),
                    None)?
                .add_output(
                    self.bob_escrow.0.try_into()?,
                    &Compiled::from_address(self.bob_escrow.1.clone(), None),
                    None)?
                .set_sequence(0, RelTime::try_from(std::time::Duration::from_secs(10*24*60*60))?.into())?.into()
        }
    }
}

impl Contract for TrustlessEscrow {
    declare! {finish, Self::cooperate}
    declare! {then, Self::use_escrow}
    declare! {non updatable}
}