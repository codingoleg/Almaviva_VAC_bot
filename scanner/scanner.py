from datetime import timedelta, datetime, date
from pytz import timezone
from random import uniform
from typing import Dict, AsyncIterable, List, Tuple

import aiohttp
import asyncio
import db
import redis
import telegram.loggers as loggers
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_reqrep import ClientResponse
from config import redis_host
from encrypting.encrypting import fernet
from .templates.ru.cities import CITIES

REDIS_CLIENT = redis.Redis(host=redis_host)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0)"
                  " Gecko/20100101 Firefox/114.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1"
}
TIMEOUT = ClientTimeout(total=30)
ALL_TIME_INTERVALS = (
    '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
    '12:00', '12:30', '13:00', '13:30', '14:00', '14:30'
)
URL = 'https://ru.almaviva-visa.services/'
API_LOGIN = 'https://ru.almaviva-visa.services/api/login'
MOSCOW_TZ = timezone('Etc/GMT-3')
YEAR = '2023'


async def run_auth(user_id: int) -> ClientResponse:
    """Tries to authorize at login api URL.
    Returns:
        ClientResponse object.
    """
    username, password = [
        fernet.decrypt(data).decode() for data in db.select_data(
            user_id, db.ACCOUNT, f'{db.USERNAME_ALMA}, {db.PASSWORD_ALMA}'
        )
    ]
    json = {"email": username, "password": password}
    async with ClientSession() as session:
        async with session.post(url=API_LOGIN, json=json) as response:
            if response.status == 200:
                # Updates auth token cookie if auth succeed
                auth_token = await response.json()
                db.update_value(
                    user_id, db.ACCOUNT, db.AUTH_TOKEN,
                    fernet.encrypt(auth_token['accessToken'].encode())
                )
            return response


class Appointment:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.headers = self.get_headers()
        self.city = fernet.decrypt(
            db.select_data(user_id, db.ACCOUNT, db.CITY)[0]).decode()
        self.attempts = db.select_data(user_id, db.ACCOUNT, db.ATTEMPTS)[0]
        self.errors = (
            aiohttp.ClientConnectionError,
            aiohttp.ClientOSError,
            asyncio.TimeoutError
        )

    def get_headers(self) -> Dict:
        """Creates headers using template and user auth token
        Returns:
            Completed headers
        """
        auth_token = db.select_data(self.user_id, db.ACCOUNT, db.AUTH_TOKEN)[0]
        headers = HEADERS
        headers["Authorization"] = 'Bearer ' + fernet.decrypt(
            auth_token).decode()
        return headers

    def get_dates_list(self) -> List[Tuple[str, str]]:
        """Returns:
            List of tuples with every date (month, day) from the start to the
            final date with one day interval, except weekend.
        """
        st_month, st_day, fin_month, fin_day = [
            data for data in db.select_data(
                self.user_id, db.ACCOUNT,
                f'{db.ST_MONTH}, {db.ST_DAY}, {db.FIN_MONTH}, {db.FIN_DAY}'
            )
        ]
        start_date = date(int(YEAR), st_month, st_day)
        final_date = date(int(YEAR), fin_month, fin_day)
        tomorrow = date.today() + timedelta(1)
        # Search only future dates
        if start_date < tomorrow:
            start_date = tomorrow

        dates_difference = int((final_date - start_date).days) + 1
        dates_list = []
        for day in range(dates_difference):
            next_day = start_date + timedelta(day)
            weekday = date(int(YEAR), next_day.month, next_day.day).weekday()
            # Skip saturdays and sundays.
            if weekday < 5:
                dates_list.append((str(next_day.month).zfill(2),
                                   str(next_day.day).zfill(2)))
        return dates_list

    async def find_free_day(self, month: str, day: str
                            ) -> AsyncIterable | None:
        """Tries to find a day with free spots.
        Yields:
            Free time interval in format 'hh:mm'.
        Returns:
            None if not authorized
        """
        # Compile api URL from user data
        url = f"{URL}api/sites/appointment-slots/?date={day}/{month}/" \
              f"{YEAR}&siteId={CITIES[self.city]['id']}"

        await asyncio.sleep(uniform(5, 10))
        while True:
            try:
                async with ClientSession(timeout=TIMEOUT) as session:
                    response = await session.get(url, headers=self.headers)
            except self.errors as error:
                loggers.log(self.user_id, str(error), loggers.ERROR)
            else:
                break

        scanning = f'Scanning... {YEAR}/{month}/{day}'
        current_time = datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')
        db.update_value(self.user_id, db.ACCOUNT, db.LAST_REQUEST,
                        current_time)
        loggers.log(self.user_id, scanning)

        if await response.json():
            try:
                for line in await response.json():
                    if line and line['freeSpots']:
                        yield line['time']
            except self.errors as error:
                loggers.log(self.user_id, error, loggers.ERROR)
        elif response.status == 401:
            return

    async def find_free_time(self, month: str, day: str, time: str) -> bool:
        """Tries to create an appointment with the completed template.
        Returns:
            True, if an appointment was successfully created.
            False otherwise.
        """
        url = f"{URL}api/sites/appointments-validation/?siteId=" \
              f"{CITIES[self.city]['id']}&appointmentDate={day}/" \
              f"{month}/{YEAR}&appointmentTime={time}&persons=1"
        await asyncio.sleep(uniform(5, 15))
        while True:
            try:
                async with ClientSession(timeout=TIMEOUT) as session:
                    response = await session.get(url=url, headers=self.headers)
            except self.errors as error:
                loggers.log(self.user_id, error, loggers.ERROR)
            else:
                break

        if await response.text() == 'true':
            success_row = (self.user_id, int(month), int(day), time,
                           self.attempts)
            db.insert_row(db.SUCCESS, '', success_row)
            db.update_value(self.user_id, db.ACCOUNT, db.ATTEMPTS, 0)
            loggers.log(self.user_id, f'{self.user_id} completed')
            return True
        elif await response.text() == 'false':
            current_time = datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')
            self.attempts += 1
            db.update_values(
                self.user_id,
                db.ACCOUNT,
                (db.LAST_REQUEST, db.ATTEMPTS),
                (current_time, self.attempts)
            )
            # Logs only 'invisible' time intervals here. Read README
            loggers.log(self.user_id, f'\t {self.user_id} [{current_time}] '
                                      f'{time} is occupied')
            return False
        else:
            loggers.log(
                self.user_id,
                f'{str(response.status)} {response.text()}: Unknown response',
                loggers.WARNING
            )

    async def run_scanning(self) -> Tuple[str, str, str] | None:
        """Runs scanning until successful appointment is created or user
        cancels scanning.
        Returns:
            Tuple(month, day, time interval) if successful appointment is
            created.
            None if dates_list is empty, because dates are invalid or expired.
        """
        dates_list = self.get_dates_list()
        if not dates_list:
            return
        while True:
            for month, day in dates_list:
                free_day = self.find_free_day(month, day)
                # Auth again in case auth token expires
                if free_day is None:
                    await run_auth(self.user_id)
                async for time in free_day:
                    # At first check cache
                    cached_time = f"{self.city}{month}{day}{time}"
                    if REDIS_CLIENT.get(cached_time) is None:
                        REDIS_CLIENT.set(cached_time, 0, ex=240)
                        if await self.find_free_time(month, day, time):
                            return month, day, time
                    else:
                        await asyncio.sleep(uniform(1, 4))
                        loggers.log(self.user_id, f'{cached_time} in cache')
