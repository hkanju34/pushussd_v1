from django.db import models


# Create your models here.
class Payload(models.Model):
    client_id = models.CharField(max_length=20)
    ptran_sdate = models.DateTimeField()
    msisdn = models.CharField(max_length=15)
    bill_no = models.CharField(max_length=20)
    bill_disc = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    trans_code = models.CharField(max_length=10)
    client_trans_id = models.CharField(max_length=20)
    tugw_trans_id = models.CharField(max_length=20)
    trans_status = models.IntegerField(default=0)  # 0: Pending, 1: Success, 2: Failed
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True)
    mcom_id = models.CharField(max_length=20,default='')
    mcom_status = models.CharField(max_length=2,default='')
    mcom_desc = models.CharField(max_length=50,default='')

    def __str__(self):
        return self.tugw_trans_id
