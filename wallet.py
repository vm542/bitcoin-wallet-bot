from bitcoinlib.wallets import HDWallet
w = HDWallet.create('Wallet1')
key1 = w.get_key()
key1.address