from aiogram.fsm.state import State, StatesGroup


class TextGeneration(StatesGroup):
    waiting_for_prompt = State()


class ImageGeneration(StatesGroup):
    waiting_for_prompt = State()


class AudioTranscription(StatesGroup):
    waiting_for_audio = State()


class PaymentComment(StatesGroup):
    waiting_for_comment = State()