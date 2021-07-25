
# Web3 powered trading bot

The goal of this project is to build a system to abstract away some of the low level complexity related to the interaction with the blockchain and to automatize trading at some extent





# Instructions 

1. Add the private information needed in `private_config.yaml` so : the Infura Endpoint, the PKs of the wallets you want the BOT to use 

2. Build the Docker Image with 

```
./build.sh
```

3. Start the Container with 

```
./run.sh
```



4. Check your wallet balance with 

```
./start.py --action check_wallet 
```

Expected result 

```
newuser@05bd4971d31a:/project$ ./start.py --action check_wallet --pcfg my_private_config.yaml 
Checking config file
OK

Checking config file
OK

Connecting to rinkeby
OK

Reading Token WETH
OK

Reading Token WBTC
OK

Building Wallets
OK

Checking WalletID=0 --> 0x8A76D6F7300F54Ce508165cc94B49974E54a77BE
Balance
{'ETH': 8996844219974559061, 'WETH': 0, 'WBTC': 10808381933}
```


NOTE 
- I am using `--pcfg my_private_config.yaml` to specify a different private config file than the one under git, for obvious reasons 






5. Try running the very simple strategy provided in `executions/swaps.yaml` with 

```
./start.py --action swap --swaps executions/swaps.yaml 
```

Expected result

```
newuser@05bd4971d31a:/project$ ./start.py --action swap --swaps executions/swaps.yaml --pcfg my_private_config.yaml
Checking config file
OK

Checking config file
OK

Connecting to rinkeby
OK

Reading Token WETH
OK

Reading Token WBTC
OK

Building Wallets
OK

Reading Dex uniswap_v2
OK
Account 0 --> 0x8A76D6F7300F54Ce508165cc94B49974E54a77BE
Balance
{'ETH': 8996844219974559061, 'WETH': 0, 'WBTC': 10808381933}
Account 1 --> 0xE392D329Bf8361685d1AB010D3f80270a4A010fa
Balance
{'ETH': 0, 'WETH': 0, 'WBTC': 0}
Executing
{'from': 'ETH', 'to': 'WETH', 'type': 'opt', 'amount': {'type': 'abs', 'val': 1000000000000}}

Wrapping ETH
Optional TX: let's check if enough WETH is already available
Not enough WETH available, let's wrap the difference 1000000000000
1000000000000 ETH --> WETH 
0xca6659c439302d2b4db34d96eca56a7f3f62029366e31da33c7a11ec5b4b81ec
Waiting for the TX to be included ...
DONE
Executing
{'to': 'WBTC', 'amount': {'type': 'perc', 'val': 1.0}}

ERC20 Tokens Exchange
Approved 1000000000000 WETH for Uniswap
0xb5f8f622ed81b3feadb988ad37c3bb68e69151e7113d1be10a81742c3e84ef31
Waiting for the TX to be included ...
DONE
{'token_sell': '0xc778417E063141139Fce010982780140Aa0cD5Ab', 'token_buy': '0x577D296678535e4903D59A4C929B718e1D575e0A', 'amount_sell': 1000000000000, 'min_amount_buy': 1, 'wallet': '0x8A76D6F7300F54Ce508165cc94B49974E54a77BE', 'max_time': 1627214299}
Swapping 1000000000000 WETH --> WBTC
0x228e0c6077e746eaaed56c8515f430667c4012bc93e212a95f2ef8e2965b4e68
Waiting for the TX to be included ...
DONE
OK
Delta
{'ETH': -186488001483904, 'WETH': 0, 'WBTC': 7377}
newuser@05bd4971d31a:/project$ 
```


