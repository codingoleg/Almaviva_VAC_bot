import calendar
from datetime import datetime, timedelta
from typing import Tuple

import db
from . import message_names as msg
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData
from aiogram.types import CallbackQuery
from scanner.templates.ru.cities import CITIES

ACT = 'act'
YEAR = 'year'
MONTH = 'month'
DAY = 'day'
CALENDAR_CALLBACK = CallbackData('simple_calendar', ACT, YEAR, MONTH, DAY)


def start():
    """Shows start"""
    btn_1 = InlineKeyboardButton(
        msg.CHOOSE_START, callback_data=msg.CALLBACK_TO_START
    )
    return InlineKeyboardMarkup().add(btn_1)


def num_of_persons():
    """Shows number of persons"""
    btn_1 = InlineKeyboardButton(msg.CHOOSE_1, callback_data=msg.CALLBACK_1)
    btn_2 = InlineKeyboardButton(msg.CHOOSE_2, callback_data=msg.CALLBACK_2)
    return InlineKeyboardMarkup().add(btn_1, btn_2)


def cities():
    """Shows cities"""
    kb = InlineKeyboardMarkup()
    for city in sorted(CITIES):
        kb.add(InlineKeyboardButton(city, callback_data=city))
    return kb


def check_acc():
    """Checks account data"""
    btn_1 = InlineKeyboardButton(
        msg.CHOOSE_YES, callback_data=msg.CALLBACK_TO_PERSON_1
    )
    btn_2 = InlineKeyboardButton(msg.CHOOSE_NO, callback_data=msg.CALLBACK_ACC)
    return InlineKeyboardMarkup().add(btn_1, btn_2)


def check_person_1(user_id: int):
    """Checks (Person 1) data"""
    num_of_persons = db.select_data(user_id, db.ACCOUNT, db.NUM_OF_PERSONS)[0]
    if num_of_persons == '1':
        go_to = msg.CALLBACK_TO_END
    else:
        go_to = msg.CALLBACK_TO_PERSON_2
    btn_1 = InlineKeyboardButton(msg.CHOOSE_YES, callback_data=go_to)
    btn_2 = InlineKeyboardButton(
        msg.CHOOSE_NO, callback_data=msg.CALLBACK_TO_PERSON_1
    )
    return InlineKeyboardMarkup().add(btn_1, btn_2)


def check_person_2():
    """Checks (Person 1) data"""
    btn_1 = InlineKeyboardButton(
        msg.CHOOSE_YES, callback_data=msg.CALLBACK_TO_END
    )
    btn_2 = InlineKeyboardButton(
        msg.CHOOSE_NO, callback_data=msg.CALLBACK_TO_PERSON_2
    )
    return InlineKeyboardMarkup().add(btn_1, btn_2)


def acc_delete():
    """Deletes account"""
    btn_1 = InlineKeyboardButton(msg.CHOOSE_YES, callback_data=msg.ACC_DELETE)
    return InlineKeyboardMarkup().add(btn_1)


def stop_scanning():
    """Stops scanning"""
    btn_1 = InlineKeyboardButton(
        msg.CHOOSE_YES, callback_data=msg.SCAN_STOPPED
    )
    return InlineKeyboardMarkup().add(btn_1)


def admin_panel():
    """Admin panel. Buttons: Start | Stop | Ban | Unban"""
    btn_1 = InlineKeyboardButton(
        msg.CHOOSE_START, callback_data=msg.CALLBACK_START
    )
    btn_2 = InlineKeyboardButton(
        msg.CHOOSE_STOP, callback_data=msg.CALLBACK_STOP
    )
    btn_3 = InlineKeyboardButton(
        msg.CHOOSE_BAN, callback_data=msg.CALLBACK_BAN
    )
    btn_4 = InlineKeyboardButton(
        msg.CHOOSE_UNBAN, callback_data=msg.CALLBACK_UNBAN
    )
    btn_5 = InlineKeyboardButton(
        msg.CHOOSE_UNBAN, callback_data=msg.CALLBACK_USER_DELETE
    )
    return InlineKeyboardMarkup(row_width=2).add(btn_1, btn_2, btn_3, btn_4,
                                                 btn_5)


class Calendar:
    def __init__(self, start_date: datetime = None):
        self.current_date = datetime.today() - timedelta(1)
        if start_date is None:
            self.start_date = self.current_date + timedelta(1)
        else:
            self.start_date = start_date
        self.ignore = "IGNORE"
        self.weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        self.prev_month = "PREV-MONTH"
        self.next_month = "NEXT-MONTH"
        self.day = 'DAY'

    async def start_calendar(
            self,
            year: int = datetime.now().year,
            month: int = datetime.now().month
    ) -> InlineKeyboardMarkup:
        """
        Creates an inline keyboard with the provided year and month
        :param int year: Year to use in the calendar,
                         if None the current year is used.
        :param int month: Month to use in the calendar,
                          if None the current month is used.
        :return: Returns InlineKeyboardMarkup object with the calendar.
        """
        inline_kb = InlineKeyboardMarkup(row_width=7)
        # for buttons with no answer
        ignore_callback = CALENDAR_CALLBACK.new(self.ignore, year, month, 0)
        # Buttons
        btn_prev_month = InlineKeyboardButton(
            "<<", callback_data=CALENDAR_CALLBACK.new(self.prev_month, year,
                                                      month, 1))
        btn_month_name = InlineKeyboardButton(
            f'{calendar.month_name[month]} {str(year)}',
            callback_data=ignore_callback
        )
        btn_next_month = InlineKeyboardButton(
            ">>", callback_data=CALENDAR_CALLBACK.new(self.next_month, year,
                                                      month, 1))
        btn_blank = InlineKeyboardButton(" ", callback_data=ignore_callback)
        # First row - Month and Year
        inline_kb.row()
        inline_kb.insert(btn_prev_month)
        inline_kb.insert(btn_month_name)
        inline_kb.insert(btn_next_month)
        # Second row - Week Days
        inline_kb.row()
        for day in self.weekdays:
            inline_kb.insert(
                InlineKeyboardButton(day, callback_data=ignore_callback))
        # Calendar rows - Days of month
        month_calendar = calendar.monthcalendar(year, month)
        for week in month_calendar:
            inline_kb.row()
            for day in week:
                if day != 0 and self.start_date <= datetime(
                        year, month, day) < self.current_date + timedelta(91):
                    btn_day = InlineKeyboardButton(
                        str(day), callback_data=CALENDAR_CALLBACK.new(
                            self.day, year, month, day))
                    inline_kb.insert(btn_day)
                else:
                    inline_kb.insert(btn_blank)

        return inline_kb

    async def process_selection(self, query: CallbackQuery,
                                data: CallbackData | dict) -> Tuple:
        """
        Process the callback_query. This method generates a new calendar if
        forward or backward is pressed. This method should be called inside
        a CallbackQueryHandler.
        :param query: callback_query, as provided by the CallbackQueryHandler
        :param data: callback_data, dictionary, set by CALENDAR_CALLBACK
        :return: Returns a tuple (Boolean,datetime), indicating if a date is
                 selected and returning the date if so.
        """
        return_data = (False, None)
        temp_date = datetime(int(data[YEAR]), int(data[MONTH]), 15)
        # processing empty buttons, answering with no action
        if data[ACT] == self.ignore:
            await query.answer(cache_time=60)
        # user picked a day button, return date
        if data[ACT] == self.day:
            # removing inline keyboard
            await query.message.delete_reply_markup()
            return_data = True, datetime(int(data[YEAR]), int(data[MONTH]),
                                         int(data[DAY]))
        # user navigates to previous month, editing message with new calendar
        if data[ACT] == self.prev_month:
            await query.answer()
            if self.start_date < temp_date:
                prev_date = temp_date - timedelta(days=31)
                await query.message.edit_reply_markup(
                    await self.start_calendar(int(prev_date.year),
                                              int(prev_date.month)))
        # user navigates to next month, editing message with new calendar
        if data['act'] == self.next_month:
            await query.answer()
            if self.current_date + timedelta(91) > temp_date:
                next_date = temp_date + timedelta(days=31)
                await query.message.edit_reply_markup(
                    await self.start_calendar(int(next_date.year),
                                              int(next_date.month)))
        # at some point user clicks DAY button, returning date
        return return_data
