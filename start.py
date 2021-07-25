#!/usr/local/bin/python3
import os
import sys
import platform
import re
import yaml
import argparse
from pathlib import Path
import time
import web3

def get_config(fn):
    print(f"Checking config file")
    f_config = Path(fn)
    assert(f_config.exists())
    with open(f_config) as f:
        config = yaml.safe_load(f)
        f.close()
    print(f"OK\n")
    return config

def get_infura(bc, pconfig):
    print(f"Connecting to {bc}")
    infura = web3.Web3(web3.HTTPProvider(endpoint_uri=pconfig['infura'][bc]))
    assert(infura is not None)
    print(f"OK\n")
    return infura

def get_blockchain(infura):
    return web3.eth.Eth(infura)


def get_erc20(config, infura, bc_name):
    with open(Path(config['contracts']['erc20']['abi'])) as f:
        abi = f.read()
    res = {}
    tokens = config['contracts']['erc20']['tokens']
    for token in tokens:
        print(f"Reading Token {token}")
        res[token] = infura.eth.contract(address=tokens[token][bc_name], abi=abi)
        print(f"OK\n")
    return res

def get_dex(config, infura, bc_name): 
    res = {}
    dex = config['contracts']['dex']
    for d in dex:
        print(f"Reading Dex {d}")
        with open(Path(config['contracts']['dex'][d]['router']['abi'])) as f:
            abi = f.read()
        res[d] = infura.eth.contract(address=dex[d]['router']['address'][bc_name], abi=abi)
        print(f"OK")
    return res


def get_wallets(pconfig):
    num_wallets = len(pconfig['wallets'])
    wallets = [None] * num_wallets
    print(f"Building Wallets")
    for i in range(num_wallets):
        wallets[i] = web3.eth.Account.privateKeyToAccount(pconfig['wallets'][i]['pk'])
    print(f"OK\n")
    return wallets

def get_balance(addr, infura, erc20=None):
    res = {
        'ETH': infura.eth.getBalance(addr)
    }
    if erc20 is not None:
        for token in erc20:
            res[token] = erc20[token].functions.balanceOf(addr).call()
    return res

def check_wallets(accounts, infura, erc20=None):
    for i in range(len(accounts)):
        addr = accounts[i].address
        print(f"Account {i} --> {addr}")
        print(f"Balance")
        print(f"{get_balance(addr=addr, infura=infura, erc20=erc20)}")

def compare_balance(b1, b2):
    res = {}
    for token in b2:
        res[token] = b2[token] - b1[token]
    return res


def approve(blockchain, erc20, account, token, amount, to, chainId=4, gas=70000):
  tx = erc20[token].functions.approve(
      to, amount
  ).buildTransaction({
      'chainId': chainId,
      'gas': gas,
      'nonce': blockchain.getTransactionCount(account.address)
  })

  signed_tx = web3.eth.Account.sign_transaction(tx, private_key=account.privateKey)

  return blockchain.send_raw_transaction(signed_tx.rawTransaction)


def ETH2WETH(blockchain, WETH, account, amount, chainId=4, gas=70000):
  tx = WETH.functions.deposit().buildTransaction({
        'chainId': chainId,
        'gas': gas,
        'value': amount, 
        'nonce': blockchain.getTransactionCount(account.address)
      })
  signed_tx = web3.eth.Account.sign_transaction(tx, private_key=account.privateKey)
  return blockchain.send_raw_transaction(signed_tx.rawTransaction)


def uniswap_v2_swap(blockchain, Uniswap_v2_Router_02, account, token_sell, token_buy, amount_sell, chainId=4, gas=200000):
    s = {
        'token_sell': token_sell,
        'token_buy': token_buy,
        'amount_sell': amount_sell,
        'min_amount_buy': 1,
        'wallet': account.address,
        'max_time': int(time.time()+10000)
    }

    print(s)
    
    tx = Uniswap_v2_Router_02.functions.swapExactTokensForTokens(
        amountIn=s['amount_sell'], amountOutMin=s['min_amount_buy'], path=[ s['token_sell'], s['token_buy'] ], to=s['wallet'], deadline=s['max_time']).buildTransaction({
            'chainId': chainId,
            'gas': gas,
            'from': account.address,
            'nonce': blockchain.getTransactionCount(account.address)
            })
    
    signed_tx = web3.eth.Account.sign_transaction(tx, private_key=account.privateKey)
    return blockchain.send_raw_transaction(signed_tx.rawTransaction)

def run_swaps(blockchain, account, swaps, chainId, erc20, uniswap):
    current_amount = 0
    last_token = ''
    for s in swaps:
        print(f"Executing\n{s}\n")
        #time.sleep(10)
        amount = s['amount']['val'] if s['amount']['type'] == 'abs' else int(current_amount * s['amount']['val'])
        if 'from' in s.keys() and s['from'] == 'ETH':
            if s['to'] != 'WETH':
                raise RuntimeError(f"Unrecognized Swap\n{s}")
            print(f"Wrapping ETH")

            if s['type'] == 'opt':
                print(f"Optional TX: let's check if enough WETH is already available")
                amount_weth = erc20['WETH'].functions.balanceOf(account.address).call()
                if amount_weth < amount:
                    actual_amount = amount - amount_weth
                    print(f"Not enough WETH available, let's wrap the difference {actual_amount}")
                    tx_hash = ETH2WETH(
                        blockchain=blockchain,
                        WETH=erc20['WETH'],
                        account=account,
                        amount = actual_amount,
                        chainId=chainId
                    )
                    print(f"{actual_amount} ETH --> WETH \n{tx_hash.hex()}")
                    print(f"Waiting for the TX to be included ...")
                    wait_for_tx_included(blockchain=blockchain, tx=tx_hash.hex())
                    print(f"DONE")
                else:
                    print(f"Enough WETH found")
            last_token = 'WETH'
            current_amount = erc20[last_token].functions.balanceOf(account.address).call()
        elif s['to'] == 'ETH':
            print(f"Unwrapping ETH")
            raise RuntimeError(f"Currently not implemented")
        else:
            print(f"ERC20 Tokens Exchange")
            #time.sleep(20)
            tx_approve = approve(
                blockchain=blockchain,
                erc20=erc20,
                account=account,
                token=last_token,
                amount=amount,
                to=uniswap.address
            )
            print(f"Approved {amount} {last_token} for Uniswap\n{tx_approve.hex()}")

            print(f"Waiting for the TX to be included ...")
            wait_for_tx_included(blockchain=blockchain, tx=tx_approve.hex())
            print(f"DONE")

            #time.sleep(10)

            tx_hash = uniswap_v2_swap(
                blockchain=blockchain,
                Uniswap_v2_Router_02=uniswap,
                account=account,
                token_sell=erc20[last_token].address,
                token_buy=erc20[s['to']].address,
                amount_sell = amount,
                chainId=chainId
            )
            print(f"Swapping {amount} {last_token} --> {s['to']}\n{tx_hash.hex()}")

            print(f"Waiting for the TX to be included ...")
            wait_for_tx_included(blockchain=blockchain, tx=tx_hash.hex())
            print(f"DONE")

            last_token = s['to']
            current_amount = erc20[last_token].functions.balanceOf(account.address).call()
            print(f"OK")

def check_tx(blockchain, tx, block_from, block_to):
    #temp = blockchain.filter('pending')
    #temp = blockchain.getBlock(block_identifier='pending', full_transactions=True) 
    temp = blockchain.filter({'fromBlock': block_from, 'toBlock': block_to})
    #temp = blockchain.filter({'fromBlock': blockchain.get_block_number() - 10, 'toBlock': 'latest'})
    for x in temp.get_all_entries():
        #print(f"Checking TX={x['transactionHash'].hex()}")
        if x['transactionHash'].hex() == tx:
            return x
    return None


def wait_for_tx_included(blockchain, tx):
    found = None
    while found is None:
        time.sleep(1)
        found = check_tx(blockchain=blockchain, tx=tx, block_from='latest', block_to='latest')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', default='config.yaml', type=str, help='Config File')
    parser.add_argument('--pcfg', default='private_config.yaml', type=str, help='Private Config File')
    parser.add_argument('--bc', default='rinkeby', type=str, help='Blockchain to connect')
    parser.add_argument('--action', default='run', type=str, help='Execute one of the supported actions: swap, check_tx, check_wallet')
    parser.add_argument('--swaps', default='executions/swaps.yaml', type=str, help='Swaps File')
    parser.add_argument('--tx', default='', type=str, help='Target TX')
    parser.add_argument('--wallet', default=0, type=int, help='Target WalletID')
    opt = parser.parse_args()

# Common Initial Config
config = get_config(fn=opt.cfg)
pconfig = get_config(fn=opt.pcfg)
infura = get_infura(bc=opt.bc, pconfig=pconfig)
blockchain = get_blockchain(infura=infura)
erc20 = get_erc20(config=config, infura=infura, bc_name=opt.bc)
accounts = get_wallets(pconfig=pconfig)


if opt.action == 'swap':
    b1 = get_balance(addr=accounts[0].address, infura=infura, erc20=erc20)
    dex = get_dex(config=config, infura=infura, bc_name=opt.bc)
    check_wallets(accounts=accounts, infura=infura, erc20=erc20)

    with open(Path(opt.swaps)) as f:
        swaps = yaml.safe_load(f.read())

    run_swaps(
        blockchain=blockchain,
        account=accounts[0],
        swaps=swaps['swaps'], 
        chainId=config['blockchains']['chain_id'][opt.bc],
        erc20=erc20,
        uniswap=dex['uniswap_v2']
    )

    b2 = get_balance(addr=accounts[0].address, infura=infura, erc20=erc20)


    print("Delta")
    delta = compare_balance(b1=b1, b2=b2)

    print(f"{delta}")

elif opt.action == 'check_tx':
    print(f"Checking TX={opt.tx}\n")
    temp = check_tx(blockchain=blockchain, tx=opt.tx)
    print(f"{temp}")

elif opt.action == 'check_wallet':
    addr = accounts[opt.wallet].address
    print(f"Checking WalletID={opt.wallet} --> {addr}")
    b = get_balance(addr=addr, infura=infura, erc20=erc20)
    print(f"Balance\n{b}")

else:
    raise RuntimeError(f"Action {opt.action} unsupported")



