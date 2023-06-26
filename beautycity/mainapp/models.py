from django.db import models
import pandas as pd
from datetime import datetime, timedelta, timezone


def _get_datetime_from_day_hour(day, hour='00:00'):
    day = day.split()[0]
    return pd.to_datetime('{}.{} {}'.format(
        day, str(datetime.now().year), hour),
        dayfirst=True).to_pydatetime().replace(tzinfo=timezone.utc)


def _get_weekday(date):
    WEEKDAY = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    return WEEKDAY[_get_datetime_from_day_hour(date).weekday()]


class Hairdressing(models.Model):
    named = models.CharField(max_length=50)
    price = models.IntegerField()

    def __str__(self):
        return '{}, стоимость {}руб.'.format(self.named, self.price)


class Client(models.Model):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=12)
    telegram_id = models.CharField(max_length=50)

    def __str__(self):
        return '{}, тел.: {}'.format(self.name, self.phone)


class Master(models.Model):
    name = models.CharField(max_length=50)
    work_day = models.CharField(max_length=25)

    def __str__(self):
        return self.name


class Registration(models.Model):
    client = models.ForeignKey(Client,
                               on_delete=models.SET_NULL,
                               null=True)
    master = models.ForeignKey(Master,
                               on_delete=models.SET_NULL,
                               null=True)
    hairdressing = models.ForeignKey(Hairdressing,
                                     on_delete=models.SET_NULL,
                                     null=True)
    date = models.DateTimeField()
    pay = models.BooleanField(default=False)

    def __str__(self):
        return '{}, записан к мастеру: {} на {}'.format(
            self.client.name,
            self.master.name,
            self.date,
            )


    def create(reg_meta):
        master = Master.objects.filter(name=reg_meta['master']).first()
        procedure = Hairdressing.objects.filter(named=reg_meta['procedure']).first()
        date = _get_datetime_from_day_hour(reg_meta['date'], reg_meta['hour'])
        clients = Client.objects.filter(name=reg_meta['name'], phone=reg_meta['phone'])
        client = None
        if not clients:
            client = Client.objects.create(
                name=reg_meta['name'],
                phone=reg_meta['phone'],
                telegram_id=reg_meta['telegram_id'])
        else:
            client = clients.first()
        
        registration = Registration.objects.create(
            client=client,
            master=master,
            hairdressing=procedure,
            date=date,
             )
        return registration != None


    def get_datatime_from_date_dict(day, hour='00:00'):
        return _get_datetime_from_day_hour(day, hour)


    def free_time():
        start_day = datetime.now()
        print(start_day)
        if start_day.hour > 18:
            start_day += timedelta(days=1)

        seven_days = list(pd.date_range(
            start_day,
            periods=7,
            freq='D').strftime('%d.%m').values)

        work_hours = list(pd.date_range(
            "10:00", "18:59",
            freq="30min").strftime('%H:%M').values)
        work_hours.remove('14:00')
        work_hours.remove('14:30')

        free_dates = {}
        masters = Master.objects.all()
        registrations = Registration.objects.filter(
            date__gt=_get_datetime_from_day_hour(seven_days[0]),
            date__lt=_get_datetime_from_day_hour(seven_days[-1],
                                                 hour='23:59'))

        for day in seven_days:
            masters_name = []
            for master in masters:
                if _get_weekday(day) in master.work_day.split(','):
                    masters_name.append(master.name)

            free_hours = {}
            for work_hour in work_hours:
                masters_hour_name = masters_name
                # TODO проверка времени
                free_hours[work_hour] = masters_hour_name.copy()
                for registration in registrations:
                    if registration.date == _get_datetime_from_day_hour(
                                    day,
                                    work_hour):
                        free_hours[work_hour].remove(registration.master.name)

            free_dates['{} {}'.format(day, (_get_weekday(day)))] = free_hours

        return free_dates


class FeedBack(models.Model):
    registration = models.ForeignKey(Registration,
                                     on_delete=models.SET_NULL,
                                     null=True)
    feed_back = models.TextField()

    def __str__(self):
        return '{}, {} {}'.format(
            self.registration.master.name,
            self.feed_back,
            self.registration.client.name)
