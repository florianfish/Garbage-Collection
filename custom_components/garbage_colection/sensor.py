"""Support for garbage_collection sensors."""
import logging
from datetime import datetime, date, timedelta

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    WEEKDAYS
)
from homeassistant.core import HomeAssistant, State
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "garbage_collection"

FREQUENCY_OPTIONS = [
    "weekly",
    "even-weeks",
    "odd-weeks",
    "monthly",
    "every-n-weeks"
]
MONTH_OPTIONS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec"
]

DEFAULT_FIRST_MONTH = "jan"
DEFAULT_LAST_MONTH = "dec"
DEFAULT_FREQUENCY = "weekly"
DEFAULT_PERIOD = 1
DEFAULT_FIRST_WEEK = 1
DEFAULT_ICON_NORMAL = "mdi:trash-can"
DEFAULT_ICON_TODAY = "mdi:delete-restore"
DEFAULT_ICON_TOMORROW = "mdi:delete-circle"
DEFAULT_VERBOSE_STATE = False

CONF_ICON_NORMAL = "icon_normal"
CONF_ICON_TODAY = "icon_today"
CONF_ICON_TOMORROW = "icon_tomorrow"
CONF_VERBOSE_STATE = "verbose_state"
CONF_FIRST_MONTH = "first_month"
CONF_LAST_MONTH = "last_month"
CONF_COLLECTION_DAYS = "collection_days"
CONF_FREQUENCY = "frequency"
CONF_MONTHLY_DAY_ORDER_NUMBER = "monthly_day_order_number"
CONF_EXCLUDE_DATES = "exclude_dates"
CONF_INCLUDE_DATES = "include_dates"
CONF_PERIOD = "period"
CONF_FIRST_WEEK = "first_week"

ATTR_NEXT_DATE = "next_date"
ATTR_DAYS = "days"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_COLLECTION_DAYS): vol.All(
        cv.ensure_list,
        [vol.In(WEEKDAYS)]
    ),
    vol.Optional(CONF_FIRST_MONTH, default=DEFAULT_FIRST_MONTH): vol.In(
        MONTH_OPTIONS
    ),
    vol.Optional(CONF_LAST_MONTH, default=DEFAULT_LAST_MONTH): vol.In(
        MONTH_OPTIONS
    ),
    vol.Optional(CONF_FREQUENCY, default=DEFAULT_FREQUENCY): vol.In(
        FREQUENCY_OPTIONS
    ),
    vol.Optional(CONF_MONTHLY_DAY_ORDER_NUMBER, default=[1]): vol.All(
        cv.ensure_list,
        [vol.All(vol.Coerce(int), vol.Range(min=1, max=5))]
    ),
    vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=52)
    ),
    vol.Optional(CONF_FIRST_WEEK, default=DEFAULT_FIRST_WEEK): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=52)
    ),
    vol.Optional(CONF_INCLUDE_DATES, default=[]): vol.All(
        cv.ensure_list,
        [cv.date]
    ),
    vol.Optional(CONF_EXCLUDE_DATES, default=[]): vol.All(
        cv.ensure_list,
        [cv.date]
    ),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_ICON_NORMAL, default=DEFAULT_ICON_NORMAL): cv.icon,
    vol.Optional(CONF_ICON_TODAY, default=DEFAULT_ICON_TODAY): cv.icon,
    vol.Optional(CONF_ICON_TOMORROW, default=DEFAULT_ICON_TOMORROW): cv.icon,
    vol.Optional(CONF_VERBOSE_STATE, default=DEFAULT_VERBOSE_STATE): cv.boolean,
})

SCAN_INTERVAL = timedelta(seconds=60)
THROTTLE_INTERVAL = timedelta(seconds=60)

TRACKABLE_DOMAINS = ["sensor"]

async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None
):
    """Setup the sensor platform."""
    async_add_entities([garbageSensor(config)], True)


def nth_weekday_date(n, date_of_month, collection_day):
    first_of_month = datetime(
        date_of_month.year,
        date_of_month.month,
        1).date()
    month_starts_on = first_of_month.weekday()
    # 1st of the month is before the day of collection
    # (so 1st collection week the week when month starts)
    if collection_day >= month_starts_on:
        return first_of_month \
            + timedelta(days=collection_day-month_starts_on+(n-1)*7)
    else:  # Next week
        return first_of_month \
            + timedelta(days=7-month_starts_on+collection_day+(n-1)*7)


class garbageSensor(Entity):

    def __init__(self, config):
        """Initialize the sensor."""
        self._name = config.get(CONF_NAME)
        self._collection_days = config.get(CONF_COLLECTION_DAYS)
        first_month = config.get(CONF_FIRST_MONTH)
        if first_month in MONTH_OPTIONS:
            self._first_month = MONTH_OPTIONS.index(first_month) + 1
        else:
            self._first_month = 1
        last_month = config.get(CONF_LAST_MONTH)
        if last_month in MONTH_OPTIONS:
            self._last_month = MONTH_OPTIONS.index(last_month) + 1
        else:
            self._last_month = 12
        self._frequency = config.get(CONF_FREQUENCY)
        self._monthly_day_order_numbers = config.get(CONF_MONTHLY_DAY_ORDER_NUMBER)
        self._include_dates = config.get(CONF_INCLUDE_DATES)
        self._exclude_dates = config.get(CONF_EXCLUDE_DATES)
        self._period = config.get(CONF_PERIOD)
        self._first_week = config.get(CONF_FIRST_WEEK)
        self._next_date = None
        self._today = None
        self._days = 0
        self._verbose_state = config.get(CONF_VERBOSE_STATE)
        self._state = '' if bool(self._verbose_state) else 2
        self._icon_normal = config.get(CONF_ICON_NORMAL)
        self._icon_today = config.get(CONF_ICON_TODAY)
        self._icon_tomorrow = config.get(CONF_ICON_TOMORROW)
        self._icon = self._icon_normal

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the name of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        res = {}
        res[ATTR_NEXT_DATE] = None if self._next_date is None else datetime(
            self._next_date.year,
            self._next_date.month,
            self._next_date.day)
        res[ATTR_DAYS] = self._days
        return res

    @property
    def icon(self):
        return self._icon

    def date_inside(self, dat):
        month = dat.month
        if self._first_month <= self._last_month:
            return bool(
                month >= self._first_month and
                month <= self._last_month)
        else:
            return bool(
                month <= self._last_month or
                month >= self._first_month)

    def find_candidate_date(self, day1):
        """Find the next possible date starting from day1,
        only based on calendar, not lookimg at include/exclude days"""
        week = day1.isocalendar()[1]
        weekday = day1.weekday()
        if self._frequency in [
                'weekly',
                'even-weeks',
                'odd-weeks',
                'every-n-weeks']:
            # Everything except montthly
            # convert to every-n-weeks
            if self._frequency == 'weekly':
                period = 1
                first_week = 1
            elif self._frequency == 'even-weeks':
                period = 2
                first_week = 2
            elif self._frequency == 'odd-weeks':
                period = 2
                first_week = 1
            else:
                period = self._period
                first_week = self._first_week
            offset = -1
            if (week - first_week) % period == 0:  # Collection this week
                for day_name in self._collection_days:
                    day_index = WEEKDAYS.index(day_name)
                    if day_index >= weekday:  # Collection still did not happen
                        offset = day_index-weekday
                        break
            if offset == -1:  # look in following weeks
                in_weeks = period - (week-first_week) % period
                offset = 7*in_weeks \
                    - weekday \
                    + WEEKDAYS.index(self._collection_days[0])
            return day1 + timedelta(days=offset)
        elif self._frequency == 'monthly':
            # Monthly
            for monthly_day_order_number in self._monthly_day_order_numbers:
                candidate_date = nth_weekday_date(
                    monthly_day_order_number,
                    day1,
                    WEEKDAYS.index(self._collection_days[0]))
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return candidate_date
            if day1.month == 12:
                next_collection_month = datetime(
                    day1.year+1,
                    1,
                    1).date()
            else:
                next_collection_month = datetime(
                    day1.year,
                    day1.month+1,
                    1).date()
            return nth_weekday_date(
                self._monthly_day_order_numbers[0],
                next_collection_month,
                WEEKDAYS.index(self._collection_days[0]))
        else:
            _LOGGER.debug(
                f"({self._name}) Unknown frequency {self._frequency}")
            return None

    def get_next_date(self, day1):
        """Find the next date starting from day1.
        Looks at include and exclude days"""
        first_day = day1
        i = 0
        while True:
            next_date = self.find_candidate_date(first_day)
            include_dates = list(filter(
                lambda date: date >= day1,
                self._include_dates))
            if len(include_dates) > 0 and include_dates[0] < next_date:
                next_date = include_dates[0]
            if next_date not in self._exclude_dates:
                break
            else:
                first_day = next_date + timedelta(days=1)
            i += 1
            if i > 365:
                _LOGGER.error("(%s) Cannot find any suitable date", self._name)
                next_date = None
                break
        return next_date

    async def async_update(self):
        """Get the latest data and updates the states."""
        today = datetime.now().date()
        if self._today is not None and self._today == today:
            # _LOGGER.debug(
            #     "(%s) Skipping the update, already did it today",
            #     self._name)
            return
        _LOGGER.debug("(%s) Calling update", self._name)
        today = datetime.now().date()
        year = today.year
        month = today.month
        self._today = today
        if self.date_inside(today):
            next_date = self.get_next_date(today)
            if next_date is not None:
                next_date_year = next_date.year
                if not self.date_inside(next_date):
                    if self._first_month <= self._last_month:
                        next_year = datetime(
                            next_date_year+1,
                            self._first_month,
                            1).date()
                        next_date = self.get_next_date(next_year)
                        _LOGGER.debug(
                            "(%s) Did not find the date this year, "
                            "lookig at next year",
                            self._name)
                    else:
                        next_year = datetime(
                            next_date_year,
                            self._first_month,
                            1).date()
                        next_date = self.get_next_date(next_year)
                        _LOGGER.debug(
                            "(%s) Arrived to the end of date range, "
                            "starting at first month",
                            self._name)
        else:
            if (self._first_month <= self._last_month and
                    month > self._last_month):
                next_year = datetime(year+1, self._first_month, 1).date()
                next_date = self.get_next_date(next_year)
                _LOGGER.debug(
                    "(%s) Date outside range, lookig at next year",
                    self._name)
            else:
                next_year = datetime(year, self._first_month, 1).date()
                next_date = self.get_next_date(next_year)
                _LOGGER.debug(
                    "(%s) Current date is outside of the range, "
                    "starting from first month",
                    self._name)
        self._next_date = next_date
        if next_date is not None:
            self._days = (self._next_date-today).days
            next_date_txt = self._next_date.strftime("%d-%b-%Y")
            _LOGGER.debug(
                "(%s) Found next date: %s, that is in %d days",
                self._name,
                next_date_txt,
                self._days)
            if self._days > 1:
                if bool(self._verbose_state):
                    self._state = f'on {next_date_txt}, in {self._days} days'
                else:
                    self._state = 2
                self._icon = self._icon_normal
            else:
                if self._days == 0:
                    if bool(self._verbose_state):
                        self._state = 'Today'
                    else:
                        self._state = self._days
                    self._icon = self._icon_today
                elif self._days == 1:
                    if bool(self._verbose_state):
                        self._state = 'Tomorrow'
                    else:
                        self._state = self._days
                    self._icon = self._icon_tomorrow
        else:
            self._days = None
