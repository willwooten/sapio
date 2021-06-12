## Setup Sapio

Sapio is written in the [Rust](https://rustup.rs/) programming language. You can learn more about Rust reading the [Rust Book](https://doc.rust-lang.org/book/), looking at the [documentation](https://doc.rust-lang.org/reference/introduction.html) or doing practice exercises with [Rustlings](https://github.com/rust-lang/rustlings). Sapio also uses [WebAssembly (WASM)](https://rustwasm.github.io/docs/book/) plugins which you can read more about [on their website](https://rustwasm.github.io/).

1. If you don't have Rust installed, go to their [website](https://rustup.rs/) to setup or run:

        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

2.  Add the wasm target by running:
   
        rustup target add wasm32-unknown-unknown

3.  Install the [wasm-pack](https://rustwasm.github.io/wasm-pack/) tool
   
4.  Clone the repo into your desired directory: 
        
        git clone git@github.com:sapio-lang/sapio.git && cd sapio

5.  Finally, build the plugin by running:
        
        cd plugin-example && wasm-pack build && cd ..

Your terminal should be in the `sapio` directory and your environment is ready to go.

## Sending a Transaction
We are going to create a contract to send a payment to a specific UTXO. The cli command we will use is `contract create` which is defined here:

    sapio   
    └─── cli
        └─── main.rs
            ├── contract - line 176
            ├── create - line 332

`contract create` takes the arguments:
* amount: the amount to send in btc
* json: a json with contract arguments
  * participants {amount, address}
  * fee_sats_per_tx
  * radix
* file: a WASM plugin file

The contract itself is located in the `plugin.rs` file, and the wasm plugin file is `sapio_wasm_plugin_example_bg.wasm.d.ts`:

    sapio   
    └─── plugin-example
        └─── src
            ├── plugin.rs
        └───pkg
            ├── sapio_wasm_plugin_example_bg.wasm.d.ts

We are ready to instantiate a contract. Before we do let's break the terminal command down:

* `cargo run --bin sapio-cli`
  * Runs the sapio-cli package located in the `cli` directory
* `contract create`
  * the cli command and subcommand
* `9.99`
  * the **amount** argument denominated in bitcoin
* `"{\"participants\": [{\"amount\": 9.99, \"address\": \"bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw\"}], \"radix\": 2, \"fee_sats_per_tx\": 0}"`
  * the **json** argument with the sub-argument: participants {amount, address}, radix, and fees_sats_per_tx
  * clean json formatted:
    ```json
    {
        "participants": [
            {
                "amount": 9.99,
                "address": "bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw"
            }
        ],
        "radix": 2, 
        "fee_sats_per_tx": 0
    }
    ```
* `--file="plugin-example/pkg/sapio_wasm_plugin_example_bg.wasm"`
  * the **file** argument
* `>> sapio-example.json`
  * saves the output as a json file

Now, in the terminal run the complete command:

    cargo run --bin sapio-cli -- contract create 9.99 "{\"participants\": [{\"amount\": 9.98009, \"address\": \"bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw\"}], \"radix\": 2, \"fee_sats_per_tx\": 1000}" --file="plugin-example/pkg/sapio_wasm_plugin_example_bg.wasm" >> sapio-example.json

After running, take a look at the saved `sapio-example.json` file. Many of the attributes will be familiar to anyone that's looked at a bitcoin transaction:

```json
{
    "template_hash_to_template_map": {
        "83de63c1d123ecdec3a982a6a7a30023edb9b9241a0ea31e8ca7a49a08fef20d": {
            "precomputed_template_hash": "83de63c1d123ecdec3a982a6a7a30023edb9b9241a0ea31e8ca7a49a08fef20d",
            "precomputed_template_hash_idx": 0,
            "max_amount_sats": 999000000,
            "transaction_literal": {
                "version": 2,
                "lock_time": 0,
                "input": [
                    {
                        "previous_output": "0000000000000000000000000000000000000000000000000000000000000000:4294967295",
                        "script_sig": "",
                        "sequence": 4194304,
                        "witness": []
                    }
                ],
                "output": [
                    {
                        "value": 999000000,
                        "script_pubkey": "001487a87e0e17a80a2d2bd65c421a1090df8ed6cc9a"
                    }
                ]
            },
            "outputs_info": [
                {
                    "sending_amount_sats": 999000000,
                    "receiving_contract": {
                        "address": "bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw",
                        "amount_range": {
                            "max_btc": 9.99
                        }
                    }
                }
            ]
        }
    },
    "known_policy": "pk(03562da39102229d6861a428460eace7df5750e89048f09aac74896143512c0e14)",
    "address": "bcrt1qxdrxld2lfxdun64wykdurtgszm4ry9fwxq647u5pl079w980kfmsdadmua",
    "known_descriptor": "wsh(pk(03562da39102229d6861a428460eace7df5750e89048f09aac74896143512c0e14))#mwz2jpj9",
    "amount_range": {
        "max_btc": 9.99
    }
}
```

## Behind the Scenes
To get a better understanding of what just happened, let's take a look at the `plugin.rs` contract file in more detail.

At the top, we have Rust `use` declarations which create local name bindings for modules necessary in the contract. 

```rust
#[deny(missing_docs)]
use sapio::contract::*;
use sapio::util::amountrange::*;
use sapio::*;
use sapio_wasm_plugin::client::*;
use sapio_wasm_plugin::*;
use schemars::*;
use serde::*;
use std::collections::VecDeque;
```

First the contract creates a public structure named **Payment** that has two fields, **amount** (denominated in bitcoin) and **address** (a bitcoin UTXO).

```rust
/// A payment to a specific address
#[derive(JsonSchema, Serialize, Deserialize, Clone)]
pub struct Payment {
    /// The amount to send
    #[serde(with = "bitcoin::util::amount::serde::as_btc")]
    #[schemars(with = "f64")]
    pub amount: bitcoin::util::amount::Amount,
    /// # Address
    /// The Address to send to
    pub address: bitcoin::Address,
}
```

Next, two more public structures are created:
* **TreePay** with the fields **participants** (a vector), **radix**, and **fees_sats_per_tx** (denominated in sats)
* **PayThese** with the fields **contracts** and **fees**

```rust
#[derive(JsonSchema, Serialize, Deserialize)]
pub struct TreePay {
    /// all of the payments needing to be sent
    pub participants: Vec<Payment>,
    /// the radix of the tree to build. Optimal for users should be around 4 or
    /// 5 (with CTV, not emulators).
    pub radix: usize,
    #[serde(with = "bitcoin::util::amount::serde::as_sat")]
    #[schemars(with = "u64")]
    pub fee_sats_per_tx: bitcoin::util::amount::Amount,
}

use bitcoin::util::amount::Amount;
struct PayThese {
    contracts: Vec<(Amount, Box<dyn Compilable>)>,
    fees: Amount,
}
```

Next we implement functionalities:
* for the **PayThese** struct, a macro `then!` and a function `total_to_pay`. 
* also for the **Contract** field inside **PayThese**, two `declare!` macros

```rust
impl PayThese {
    then! {
        fn expand(self, ctx) {
            let mut bld = ctx.template();
            for (amt, ct) in self.contracts.iter() {
                bld = bld.add_output(*amt, ct.as_ref(), None)?;
            }
            bld.add_fees(self.fees)?.into()
        }
    }

    fn total_to_pay(&self) -> Amount {
        let mut amt = self.fees;
        for (x, _) in self.contracts.iter() {
            amt += *x;
        }
        amt
    }
}

impl Contract for PayThese {
    declare! {then, Self::expand}
    declare! {non updatable}
}
```

Next we do the same for the **TreePay** struct and **Contract** field inside.

```rust
impl TreePay {
    then! {
        fn expand(self, ctx) {

            let mut queue : VecDeque<(Amount, Box<dyn Compilable>)> = self.participants.iter().map(|payment| {
                let mut amt = AmountRange::new();
                amt.update_range(payment.amount);
                let b : Box::<dyn Compilable> = Box::new(Compiled::from_address(payment.address.clone(), Some(amt)));
                (payment.amount, b)
            }).collect();

            loop {
                let v : Vec<_> = queue.drain(0..std::cmp::min(self.radix, queue.len())).collect();
                if queue.len() == 0 {
                    let mut builder = ctx.template();
                    for pay in v.iter() {
                        builder = builder.add_output(pay.0, pay.1.as_ref(), None)?;
                    }
                    builder =builder.add_fees(self.fee_sats_per_tx)?;
                    return builder.into();
                } else {
                    let pay = Box::new(PayThese{contracts:v, fees: self.fee_sats_per_tx});
                    queue.push_back((pay.total_to_pay(), pay))
                }
            }
    }}
}

impl Contract for TreePay {
    declare! {then, Self::expand}
    declare! {non updatable}
}
```

Lastly, we output **TreePay** struct, which above was saved as `sapio-example.json`:

```rust
REGISTER![TreePay];
```