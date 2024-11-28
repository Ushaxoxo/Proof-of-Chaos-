class TokenContract:
    def __init__(self, name, symbol, total_supply, creator_address):
        """
        Initialize the token contract.
        :param name: Name of the token
        :param symbol: Symbol of the token
        :param total_supply: Total supply of the token
        :param creator_address: Address of the token creator
        """
        self.name = name
        self.symbol = symbol
        self.total_supply = total_supply
        self.balances = {creator_address: total_supply}  # Assign all tokens to the creator
        self.allowances = {}  # {owner: {spender: amount}}

    def transfer(self, sender, receiver, amount):
        """
        Transfer tokens from the sender to the receiver.
        :param sender: Address of the sender
        :param receiver: Address of the receiver
        :param amount: Amount of tokens to transfer
        :return: True if successful, raises Exception otherwise
        """
        if sender not in self.balances or self.balances[sender] < amount:
            raise Exception("Insufficient balance")
        if amount <= 0:
            raise Exception("Transfer amount must be greater than 0")

        # Deduct from sender and add to receiver
        self.balances[sender] -= amount
        self.balances[receiver] = self.balances.get(receiver, 0) + amount
        return True

    def balance_of(self, address):
        """
        Get the token balance of a specific address.
        :param address: Address to query
        :return: Balance of the address
        """
        return self.balances.get(address, 0)

    def approve(self, owner, spender, amount):
        """
        Approve a spender to use tokens on behalf of the owner.
        :param owner: Address of the token owner
        :param spender: Address of the spender
        :param amount: Amount of tokens to approve
        :return: True if successful
        """
        if owner not in self.balances or self.balances[owner] < amount:
            raise Exception("Insufficient balance to approve")
        if amount <= 0:
            raise Exception("Approval amount must be greater than 0")

        if owner not in self.allowances:
            self.allowances[owner] = {}
        self.allowances[owner][spender] = amount
        return True

    def allowance(self, owner, spender):
        
        return self.allowances.get(owner, {}).get(spender, 0)

    def transfer_from(self, owner, spender, receiver, amount):
       
        allowed_amount = self.allowance(owner, spender)
        if allowed_amount < amount:
            raise Exception("Transfer amount exceeds allowance")
        if self.balances.get(owner, 0) < amount:
            raise Exception("Insufficient balance in owner's account")
        if amount <= 0:
            raise Exception("Transfer amount must be greater than 0")

        # Deduct from owner and allowance, add to receiver
        self.balances[owner] -= amount
        self.allowances[owner][spender] -= amount
        self.balances[receiver] = self.balances.get(receiver, 0) + amount
        return True
