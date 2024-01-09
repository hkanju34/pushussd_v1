from django.urls import path
from . import views
from agservice.views import Pushagr,PushMngnt,AddUser
from django_cron import CronJobManager




urlpatterns = [
    path('ussdpush/bill/v1/', Pushagr.as_view(), name='get_bill_data'),
    path('ussdpush/mngnt/v1/', PushMngnt.as_view(), name='push_mngnt'),
    path('ussdpush/adduser/v1/', AddUser.as_view(), name='push_mngnt'),
    path('ussdpush/transrepo/v1/', views.trans_records, name='transrecords'),
]

