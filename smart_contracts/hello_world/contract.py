from puyapy import (
    ARC4Contract,
    UInt64,
    Bytes,
    Global,
    Local,
    arc4,
    subroutine,
    Transaction,
    CreateInnerTransaction,
    PaymentTransaction,
    TransactionType,
    AssetHoldingGet,
    app_opted_in,
    InnerTransaction,
)
from puyapy.arc4 import abimethod, baremethod


class HelloWorld(ARC4Contract):
    def __init__(self) -> None:
        self.goal = arc4.UInt64(0)
        self.detail = arc4.String
        self.title = arc4.String
        self.fund_raised = arc4.UInt64(0)
        self.donator_num = arc4.UInt64(0)
        self.min_donation = arc4.UInt64(0)
        self.active = arc4.UInt64(0)
        self.reward_nft_id = arc4.UInt64(0)
        self.donator_info = Local(arc4.UInt64)

    @baremethod(create=True)
    def create(self) -> None:
        """Allow creates"""

    @subroutine
    def _authorize_creator(self) -> None:
        assert Global.creator_address() == Transaction.sender()

    @subroutine
    def _opt_in_asset(self, asset_id: UInt64) -> None:
        self._authorize_creator()

        CreateInnerTransaction.begin()
        CreateInnerTransaction.set_type_enum(TransactionType.AssetTransfer)
        CreateInnerTransaction.set_fee(UInt64(0))
        CreateInnerTransaction.set_asset_receiver(Global.current_application_address())
        CreateInnerTransaction.set_xfer_asset(asset_id)
        CreateInnerTransaction.submit()

    @abimethod()
    def bootstrap(
        self,
        goal: arc4.UInt64,
        detail: arc4.String,
        title: arc4.String,
        min_donation: arc4.UInt64,
        asset_name: arc4.String,
        unit_name: arc4.String,
        nft_amount: arc4.UInt64,
        asset_url: arc4.String,
        mbr_pay: PaymentTransaction,
    ) -> arc4.UInt64:
        self._authorize_creator()

        assert mbr_pay.amount >= Global.min_balance()
        assert mbr_pay.receiver == Global.current_application_address()
        assert mbr_pay.sender == Global.creator_address()

        self.goal = goal
        self.detail = arc4.String(detail)
        self.title = title
        self.min_donation = min_donation
        self.fund_raised = arc4.UInt64(0)
        self.active = arc4.UInt64(1)

        CreateInnerTransaction.begin()
        CreateInnerTransaction.set_type_enum(TransactionType.AssetConfig)
        CreateInnerTransaction.set_fee(0)
        CreateInnerTransaction.set_config_asset_name(asset_name)
        CreateInnerTransaction.set_config_asset_unit_name(unit_name)
        CreateInnerTransaction.set_config_asset_url(asset_url)
        CreateInnerTransaction.set_config_asset_total(nft_amount)
        CreateInnerTransaction.set_config_asset_decimals(0)
        CreateInnerTransaction.submit()

        self.reward_nft_id = InnerTransaction.created_asset_id()
        return self.reward_nft_id

    @baremethod(allow_actions=["OptIn"])
    def opt_in_to_app(self) -> None:
        self.donator_info[Transaction.sender()] = 0

    @abimethod
    def fund(self, fund_pay: PaymentTransaction) -> None:
        fund_amount = fund_pay.amount
        total_fund = self.fund_raised

        assert app_opted_in(Transaction.sender(), Global.current_application_id())
        assert self.active == 1
        assert fund_amount >= self.min_donation
        assert fund_pay.receiver == Global.current_application_address()
        assert fund_pay.sender == Transaction.sender()

        new_donation_amount = self.donator_info[Transaction.sender()] + fund_amount
        self.donator_info[Transaction.sender()] = new_donation_amount
        self.dontaor_num = self.dontaor_num + 1
        self.fund_raised = total_fund + fund_amount

        asset_holding = AssetHoldingGet.asset_balance(
            Transaction.sender(), self.reward_nft_id
        )

        if asset_holding[1] == 1:
            asa_balance = asset_holding[0]
            if asa_balance == 0:
                CreateInnerTransaction.begin()
                CreateInnerTransaction.set_type_enum(TransactionType.AssetTransfer)
                CreateInnerTransaction.set_fee(0)
                CreateInnerTransaction.set_asset_receiver(Transaction.sender())
                CreateInnerTransaction.set_xfer_asset(self.reward_nft_id)
                CreateInnerTransaction.set_asset_amount(1)
                CreateInnerTransaction.submit()

    @abimethod
    def claim_fund(self) -> arc4.UInt64:
        self._authorize_creator()

        total_raised_funds = self.fund_raised

        CreateInnerTransaction.begin()
        CreateInnerTransaction.set_type_enum(TransactionType.Payment)
        CreateInnerTransaction.set_fee(0)
        CreateInnerTransaction.set_payment_receiver(Transaction.sender())
        CreateInnerTransaction.set_payment_amount(total_raised_funds)
        CreateInnerTransaction.submit()

    @baremethod(allow_actions=["DeleteApplication"])
    def delete_application(self) -> None:
        self._authorize_creator()

        assert self.active == 0
        assert self.fund_raised == 0
