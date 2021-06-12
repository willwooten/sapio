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

Your terminal should be in the `sapio` directory and your environment is be ready to go.

## Sending a Transaction
We are going to create a contract to send a payment to a specific UTXO. The cli command we will use is `contract create` which is defined here:

    sapio   
    └─── cli
        └─── main.rs
            |   contract - line 176
            |   create - line 332

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
            └─── plugin.rs
        └───pkg
            └─── sapio_wasm_plugin_example_bg.wasm.d.ts

We are ready to instantiate a contract. Before we do let's break the terminal command down:

* `cargo run --bin sapio-cli`
  * Runs the sapio-cli package located in the `cli` directory
* `contract create`
  * the cli command and subcommand
* `9.99`
  * the **amount** argument in denominated in bitcoin
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

    cargo run --bin sapio-cli -- contract create 9.99 "{\"participants\": [{\"amount\": 9.99, \"address\": \"bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw\"}], \"radix\": 2, \"fee_sats_per_tx\": 0}" --file="plugin-example/pkg/sapio_wasm_plugin_example_bg.wasm" >> sapio-example.json

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