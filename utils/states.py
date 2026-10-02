from aiogram.fsm.state import State, StatesGroup


class WithdrawalStates(StatesGroup):
    waiting_amount = State()
    waiting_destination = State()


class AdminCreditStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


class AdminSpinStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


class AdminTaskStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_type = State()
    waiting_link = State()
    waiting_reward = State()
    waiting_max = State()
    waiting_order = State()
    waiting_verify = State()
    waiting_active = State()


class AdminChanceStates(StatesGroup):
    waiting_chance = State()


class AdminBroadcastStates(StatesGroup):
    waiting_type = State()
    waiting_content = State()
    waiting_button_text = State()
    waiting_button_url = State()


class AdminChannelStates(StatesGroup):
    waiting_username = State()
    waiting_chat_id = State()


class AdminSettingStates(StatesGroup):
    waiting_min_withdrawal = State()
    waiting_support_username = State()


class AdminPayoutMethodStates(StatesGroup):
    waiting_name = State()
    waiting_kind = State()
